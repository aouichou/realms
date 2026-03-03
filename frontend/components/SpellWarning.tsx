'use client';

import { AlertTriangle, Lightbulb, Sparkles, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface SpellWarningProps {
	message: string;
	type?: 'warning' | 'suggestion' | 'error';
	onDismiss?: () => void;
	duration?: number;
}

export function SpellWarning({ message, type = 'warning', onDismiss, duration = 5000 }: SpellWarningProps) {
	const [isVisible, setIsVisible] = useState(true);
	const [isExiting, setIsExiting] = useState(false);

	const handleDismiss = useCallback(() => {
		setIsExiting(true);
		setTimeout(() => {
			setIsVisible(false);
			onDismiss?.();
		}, 300);
	}, [onDismiss]);

	useEffect(() => {
		if (duration > 0) {
			const timer = setTimeout(() => {
				handleDismiss();
			}, duration);

			return () => clearTimeout(timer);
		}
	}, [duration, handleDismiss]);

	if (!isVisible) return null;

	const getIcon = () => {
		switch (type) {
			case 'suggestion':
				return <Lightbulb className="w-5 h-5 text-accent-400" />;
			case 'error':
				return <AlertTriangle className="w-5 h-5 text-red-500" />;
			default:
				return <Sparkles className="w-5 h-5 text-accent-400" />;
		}
	};

	const getStyles = () => {
		const baseStyles = 'backdrop-blur-md border shadow-lg rounded-xl';
		switch (type) {
			case 'suggestion':
				return `${baseStyles} bg-accent-200/20 border-accent-400/40`;
			case 'error':
				return `${baseStyles} bg-red-500/10 border-red-500/40`;
			default:
				return `${baseStyles} bg-primary-900/10 border-primary-900/40`;
		}
	};

	return (
		<div
			className={`
				${getStyles()}
				p-4 flex items-start gap-3
				transform transition-all duration-300 ease-in-out
				${isExiting ? 'opacity-0 scale-95 translate-y-2' : 'opacity-100 scale-100 translate-y-0'}
			`}
		>
			<div className="shrink-0 mt-0.5">{getIcon()}</div>

			<div className="flex-1 font-body text-sm leading-relaxed text-neutral-900">
				{message}
			</div>

			<button
				onClick={handleDismiss}
				className="shrink-0 text-accent-200/70 hover:text-accent-200 transition-colors"
				aria-label="Dismiss"
			>
				<X className="w-4 h-4" />
			</button>
		</div>
	);
}
