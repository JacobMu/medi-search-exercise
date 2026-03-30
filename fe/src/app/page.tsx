"use client";

import { FileUpload } from "@/composer/components/FileUpload";
import { ResultPanel } from "@/composer/components/ResultPanel";
import { StarRating } from "@/composer/components/StarRating";
import { useCompose } from "@/composer/hooks/useCompose";
import { useState } from "react";

export default function ComposerPage() {
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null);
  const [rating, setRating] = useState<number>(0);
  const [hasRated, setHasRated] = useState<boolean>(false);

  const { state, submit, rate, reset } = useCompose();
  const { phase, outputUrl, jobId, errorMessage } = state;

  const isLoading = phase === "uploading" || phase === "polling";
  const canSubmit = avatarFile !== null && screenshotFile !== null && phase === "idle";

  const handleGenerate = () => {
    if (avatarFile && screenshotFile) {
      submit(avatarFile, screenshotFile);
    }
  };

  const handleRate = (value: number) => {
    setRating(value);
    rate(value);
    setHasRated(true);
  };

  const handleReset = () => {
    reset();
    setAvatarFile(null);
    setScreenshotFile(null);
    setRating(0);
    setHasRated(false);
  };

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Composer</h1>

      <div className="flex gap-6 mb-6">
        <FileUpload label="Avatar Image" value={avatarFile} onChange={setAvatarFile} />
        <FileUpload label="Screenshot Image" value={screenshotFile} onChange={setScreenshotFile} />
      </div>

      <button
        type="button"
        onClick={handleGenerate}
        disabled={!canSubmit}
        className={[
          "px-6 py-2 rounded bg-blue-600 text-white font-medium text-sm",
          canSubmit ? "hover:bg-blue-700" : "opacity-50 cursor-not-allowed",
        ].join(" ")}
      >
        Generate
      </button>

      {isLoading && (
        <div className="flex items-center gap-3 mt-6">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-gray-600">
            {phase === "uploading" ? "Uploading…" : "Processing…"}
          </span>
        </div>
      )}

      {phase === "error" && (
        <div className="mt-6 text-red-600 bg-red-50 rounded p-2 text-sm">{errorMessage}</div>
      )}

      {phase === "done" && outputUrl && jobId && (
        <div className="mt-6 flex flex-col gap-4">
          <ResultPanel outputUrl={outputUrl} jobId={jobId} />

          {hasRated ? (
            <p className="text-sm text-green-700 font-medium">Thank you!</p>
          ) : (
            <StarRating value={rating} onRate={handleRate} />
          )}
        </div>
      )}

      {(phase === "done" || phase === "error") && (
        <button
          type="button"
          onClick={handleReset}
          className="mt-4 px-4 py-2 rounded border border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
        >
          Reset / Start Over
        </button>
      )}
    </main>
  );
}
