"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

interface FileUploadProps {
  label: string;
  accept?: string;
  value: File | null;
  onChange: (file: File | null) => void;
}

export function FileUpload({
  label,
  accept = "image/png,image/jpeg,image/webp",
  value,
  onChange,
}: FileUploadProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!value) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(value);
    setPreviewUrl(url);
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [value]);

  const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/webp"];

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    if (file && !ALLOWED_TYPES.includes(file.type)) {
      e.target.value = "";
      onChange(null);
      return;
    }
    onChange(file);
  };

  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-2 cursor-pointer">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded bg-white text-sm text-gray-600 hover:bg-gray-50">
          Choose file
        </span>
        <input type="file" accept={accept} className="sr-only" onChange={handleChange} />
      </label>
      {previewUrl && (
        <Image
          src={previewUrl}
          alt={value?.name ?? "preview"}
          width={320}
          height={160}
          unoptimized
          className="max-w-xs max-h-40 rounded border object-contain"
        />
      )}
    </div>
  );
}
