import { Dices } from 'lucide-react';
import { useEffect, useState } from 'react';

interface DMRollingIndicatorProps {
	npcName?: string;
	rollType?: string;
}

export default function DMRollingIndicator({ npcName, rollType }: DMRollingIndicatorProps) {
	const [dots, setDots] = useState('');

	useEffect(() => {
		const interval = setInterval(() => {
			setDots(prev => {
				if (prev === '...') return '';
				return prev + '.';
			});
		}, 400);

		return () => clearInterval(interval);
	}, []);

	const formatRollType = (type?: string) => {
		if (!type) return '';
		return type
			.split('_')
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	};

	return (
		<div className="flex items-center gap-3 p-4 my-3 bg-linear-to-r from-purple-100 to-pink-100 border-2 border-purple-300 rounded-lg animate-pulse-soft">
			{/* Animated dice icon */}
			<div className="relative">
				<Dices className="w-6 h-6 text-purple-600 animate-spin-slow" />
				<div className="absolute inset-0 bg-purple-400 rounded-full blur-md opacity-30 animate-pulse" />
			</div>

			{/* Text */}
			<div className="flex-1">
				<div className="font-bold text-purple-900">
					🎲 DM is rolling{npcName && ` for ${npcName}`}{dots}
				</div>
				{rollType && (
					<div className="text-sm text-purple-700">
						{formatRollType(rollType)}
					</div>
				)}
			</div>

			{/* Animated background effect */}
			<div className="absolute inset-0 bg-linear-to-r from-purple-200/0 via-purple-300/20 to-purple-200/0 animate-shimmer" />
		</div>
	);
}

// Add CSS animations
const styles = `
@keyframes pulse-soft {
	0%, 100% {
		opacity: 1;
	}
	50% {
		opacity: 0.85;
	}
}

@keyframes spin-slow {
	from {
		transform: rotate(0deg);
	}
	to {
		transform: rotate(360deg);
	}
}

@keyframes shimmer {
	0% {
		transform: translateX(-100%);
	}
	100% {
		transform: translateX(100%);
	}
}

.animate-pulse-soft {
	animation: pulse-soft 2s ease-in-out infinite;
}

.animate-spin-slow {
	animation: spin-slow 2s linear infinite;
}

.animate-shimmer {
	animation: shimmer 2s ease-in-out infinite;
}
`;

// Inject styles
if (typeof document !== 'undefined') {
	const styleSheet = document.createElement('style');
	styleSheet.textContent = styles;
	document.head.appendChild(styleSheet);
}
