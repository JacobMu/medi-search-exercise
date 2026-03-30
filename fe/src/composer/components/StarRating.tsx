"use client";

import { useState } from "react";

interface StarRatingProps {
  value: number;
  onRate: (rating: number) => void;
  disabled?: boolean;
}

export function StarRating({ value, onRate, disabled = false }: StarRatingProps) {
  const [hovered, setHovered] = useState<number>(0);

  return (
    <fieldset className="flex gap-1 border-0 p-0 m-0">
      <legend className="sr-only">Star rating</legend>
      {[1, 2, 3, 4, 5].map((star) => {
        const isActive = star <= value;
        const isHighlighted = !disabled && star <= hovered;
        return (
          <button
            key={star}
            type="button"
            data-active={String(isActive)}
            disabled={disabled}
            className={[
              "text-2xl leading-none transition-colors",
              disabled ? "cursor-default" : "cursor-pointer",
              isActive || isHighlighted ? "text-yellow-400" : "text-gray-300",
            ].join(" ")}
            onClick={disabled ? undefined : () => onRate(star)}
            onMouseEnter={disabled ? undefined : () => setHovered(star)}
            onMouseLeave={disabled ? undefined : () => setHovered(0)}
            aria-label={`Rate ${star} star${star !== 1 ? "s" : ""}`}
          >
            {isActive || isHighlighted ? "★" : "☆"}
          </button>
        );
      })}
    </fieldset>
  );
}
