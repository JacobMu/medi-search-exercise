import type { RatingDistribution } from "@/lib/types";

interface RatingBarProps {
	distribution: RatingDistribution;
}

const STARS = [5, 4, 3, 2, 1] as const;

export function RatingBar({ distribution }: RatingBarProps) {
	const max = Math.max(
		...STARS.map((s) => distribution[String(s) as keyof RatingDistribution]),
	);

	return (
		<div>
			{STARS.map((star) => {
				const count = distribution[String(star) as keyof RatingDistribution];
				const widthPct = max === 0 ? 0 : Math.round((count / max) * 100);
				return (
					<div
						key={star}
						data-testid={`rating-bar-${star}`}
						className="flex items-center gap-3 mb-2"
					>
						<span className="w-6 text-sm text-gray-600 text-right">
							{star}★
						</span>
						<div className="flex-1 bg-gray-100 rounded-full h-4">
							<div
								data-testid={`rating-bar-fill-${star}`}
								className="bg-yellow-400 h-4 rounded-full"
								style={{ width: `${widthPct}%` }}
							/>
						</div>
						<span className="w-6 text-sm text-gray-600">{count}</span>
					</div>
				);
			})}
		</div>
	);
}
