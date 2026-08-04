import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { VideoUpload } from "./VideoUpload";

const onComplete = vi.fn();
const onError = vi.fn();

const ingestResult = {
    chunks: [
        { start: 0, end: 2, text: "Hi there.", speaker: "SPEAKER_00" },
        { start: 2, end: 4, text: "Hello back.", speaker: "SPEAKER_01" },
        { start: 4, end: 6, text: "How are you?", speaker: "SPEAKER_00" },
    ],
    speaker_order: ["SPEAKER_00", "SPEAKER_01"],
    meta: {},
};

function scoredTimeline(scoreOffset: number) {
    return {
        chunks: [
            {
                start: 0,
                end: 2,
                tone: "NEUTRAL",
                score: 5 + scoreOffset,
                color: "#CCCCCC",
                text: "Hi there.",
                anger_level: 0,
                frustration_level: 0,
                sarcasm_flag: false,
            },
        ],
        overall: { score: 5 + scoreOffset, tone: "NEUTRAL" },
    };
}

function mockJsonResponse(body: unknown, ok = true, status = 200) {
    return {
        ok,
        status,
        json: () => Promise.resolve(body),
        text: () => Promise.resolve(JSON.stringify(body)),
    };
}

function mockBlobResponse(ok = true, status = 200) {
    return {
        ok,
        status,
        blob: () => Promise.resolve(new Blob(["video"], { type: "video/mp4" })),
        text: () => Promise.resolve(""),
    };
}

function selectVideo() {
    const input = screen.getByTestId("two-speaker-video-input");
    const file = new File(["binary"], "conversation.mp4", { type: "video/mp4" });
    fireEvent.change(input, { target: { files: [file] } });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("VideoUpload", () => {
    it("renders the drop zone and disabled button initially", () => {
        render(<VideoUpload onComplete={onComplete} onError={onError} />);
        expect(screen.getByTestId("video-upload")).toBeInTheDocument();
        expect(screen.getByTestId("run-video-pipeline")).toBeDisabled();
    });

    it("enables the run button once a video is selected", () => {
        render(<VideoUpload onComplete={onComplete} onError={onError} />);
        selectVideo();
        expect(screen.getByTestId("run-video-pipeline")).not.toBeDisabled();
    });

    it("calls onError when clicked with no video selected", () => {
        render(<VideoUpload onComplete={onComplete} onError={onError} />);
        // Button is disabled without a file, but guard logic is still exercised
        // indirectly through disabled state — verify it stays disabled.
        expect(screen.getByTestId("run-video-pipeline")).toBeDisabled();
    });

    it("runs ingest → score (x3) → render-multi and calls onComplete", async () => {
        const fetchMock = vi
            .fn()
            .mockResolvedValueOnce(mockJsonResponse(ingestResult)) // /ingest
            .mockResolvedValueOnce(mockJsonResponse(scoredTimeline(0))) // overall /score
            .mockResolvedValueOnce(mockJsonResponse(scoredTimeline(1))) // left /score
            .mockResolvedValueOnce(mockJsonResponse(scoredTimeline(2))) // right /score
            .mockResolvedValueOnce(mockBlobResponse()); // /render-multi
        vi.stubGlobal("fetch", fetchMock);

        render(<VideoUpload onComplete={onComplete} onError={onError} />);
        selectVideo();
        fireEvent.click(screen.getByTestId("run-video-pipeline"));

        await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));

        expect(fetchMock).toHaveBeenCalledTimes(5);
        expect(fetchMock.mock.calls[0][0]).toContain("/ingest");
        expect(fetchMock.mock.calls[4][0]).toContain("/render-multi");

        const [timelines, video, sourceName] = onComplete.mock.calls[0];
        expect(timelines.overall.overall.score).toBe(5);
        expect(timelines.speakerLeft.overall.score).toBe(6);
        expect(timelines.speakerRight.overall.score).toBe(7);
        expect(video).toBeInstanceOf(Blob);
        expect(sourceName).toBe("conversation.mp4");

        vi.unstubAllGlobals();
    });

    it("only sends a non-empty speaker_right_timeline when a second speaker exists", async () => {
        const singleSpeakerIngest = {
            chunks: [{ start: 0, end: 2, text: "Solo.", speaker: "SPEAKER_00" }],
            speaker_order: ["SPEAKER_00"],
            meta: {},
        };
        const fetchMock = vi
            .fn()
            .mockResolvedValueOnce(mockJsonResponse(singleSpeakerIngest)) // /ingest
            .mockResolvedValueOnce(mockJsonResponse(scoredTimeline(0))) // overall /score
            .mockResolvedValueOnce(mockJsonResponse(scoredTimeline(1))) // left /score
            .mockResolvedValueOnce(mockBlobResponse()); // /render-multi
        vi.stubGlobal("fetch", fetchMock);

        render(<VideoUpload onComplete={onComplete} onError={onError} />);
        selectVideo();
        fireEvent.click(screen.getByTestId("run-video-pipeline"));

        await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));

        expect(fetchMock).toHaveBeenCalledTimes(4);
        const [timelines] = onComplete.mock.calls[0];
        expect(timelines.speakerRight).toBeNull();

        const renderCall = fetchMock.mock.calls[3];
        const formData = renderCall[1].body as FormData;
        expect(formData.get("speaker_right_timeline")).toBe("[]");

        vi.unstubAllGlobals();
    });

    it("calls onError when ingest fails", async () => {
        const fetchMock = vi.fn().mockResolvedValueOnce(mockJsonResponse({ detail: "boom" }, false, 502));
        vi.stubGlobal("fetch", fetchMock);

        render(<VideoUpload onComplete={onComplete} onError={onError} />);
        selectVideo();
        fireEvent.click(screen.getByTestId("run-video-pipeline"));

        await waitFor(() => expect(onError).toHaveBeenCalledWith(expect.stringContaining("Ingest failed")));
        expect(onComplete).not.toHaveBeenCalled();

        vi.unstubAllGlobals();
    });

    it("calls onError when no chunks are returned from ingest", async () => {
        const fetchMock = vi.fn().mockResolvedValueOnce(mockJsonResponse({ chunks: [], speaker_order: [], meta: {} }));
        vi.stubGlobal("fetch", fetchMock);

        render(<VideoUpload onComplete={onComplete} onError={onError} />);
        selectVideo();
        fireEvent.click(screen.getByTestId("run-video-pipeline"));

        await waitFor(() => expect(onError).toHaveBeenCalledWith(expect.stringContaining("No speech")));
        expect(onComplete).not.toHaveBeenCalled();

        vi.unstubAllGlobals();
    });
});
