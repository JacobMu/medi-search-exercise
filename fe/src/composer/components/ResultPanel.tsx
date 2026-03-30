interface ResultPanelProps {
	outputUrl: string;
	jobId: string;
}

export function ResultPanel({ outputUrl, jobId }: ResultPanelProps) {
	return (
		<div className="flex flex-col gap-4 items-start">
			<img
				src={outputUrl}
				alt="Composited result"
				className="max-w-full rounded shadow"
			/>
			<a
				href={outputUrl}
				download={`${jobId}.png`}
				className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
			>
				Download
			</a>
		</div>
	);
}
