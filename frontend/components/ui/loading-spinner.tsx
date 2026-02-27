import { useTranslation } from "@/lib/hooks/useTranslation";

export function LoadingSpinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
	const { t } = useTranslation();
	const sizeClasses = {
		sm: "w-4 h-4 border-2",
		md: "w-8 h-8 border-3",
		lg: "w-12 h-12 border-4",
	};

	return (
		<div className="flex items-center justify-center">
			<div
				className={`
          ${sizeClasses[size]}
          border-primary-900 border-t-transparent
          rounded-full animate-spin
        `}
				role="status"
				aria-label="Loading"
			>
				<span className="sr-only">{t('common.loading')}</span>
			</div>
		</div>
	);
}
