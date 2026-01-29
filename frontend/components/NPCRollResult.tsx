import { Brain, Dices, Shield, Skull, Swords, Zap } from 'lucide-react';
import { useEffect, useState } from 'react';

interface NPCRollData {
	npc_name: string;
	roll_type: string;
	result: number;
	breakdown: string;
	rolls: number[];
	modifier: number;
	target_name?: string;
	context?: string;
}

interface NPCRollResultProps {
	roll: NPCRollData;
}

export default function NPCRollResult({ roll }: NPCRollResultProps) {
	const [isAnimating, setIsAnimating] = useState(true);

	useEffect(() => {
		const timer = setTimeout(() => setIsAnimating(false), 600);
		return () => clearTimeout(timer);
	}, []);

	const getRollIcon = (type: string) => {
		switch (type) {
			case 'attack':
				return <Swords className="w-4 h-4" />;
			case 'damage':
				return <Skull className="w-4 h-4" />;
			case 'saving_throw':
				return <Shield className="w-4 h-4" />;
			case 'ability_check':
				return <Brain className="w-4 h-4" />;
			case 'initiative':
				return <Zap className="w-4 h-4" />;
			default:
				return <Dices className="w-4 h-4" />;
		}
	};

	const getRollColor = (type: string) => {
		switch (type) {
			case 'attack':
				return 'from-red-500 to-orange-500';
			case 'damage':
				return 'from-red-600 to-red-700';
			case 'saving_throw':
				return 'from-blue-500 to-indigo-500';
			case 'ability_check':
				return 'from-purple-500 to-pink-500';
			case 'initiative':
				return 'from-yellow-500 to-orange-500';
			default:
				return 'from-gray-500 to-gray-600';
		}
	};

	const formatRollType = (type: string) => {
		return type
			.split('_')
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	};

	const isCritical = roll.rolls.length === 1 && roll.rolls[0] === 20;
	const isCriticalFail = roll.rolls.length === 1 && roll.rolls[0] === 1;

	return (
		<div
			className={`
				relative overflow-hidden rounded-lg border-2
				${isCritical ? 'border-yellow-400 bg-yellow-50' :
					isCriticalFail ? 'border-red-500 bg-red-50' :
						'border-purple-300 bg-linear-to-r from-purple-50 to-pink-50'}
				shadow-lg
				${isAnimating ? 'animate-bounce-in' : ''}
				my-3 p-4
			`}
		>
			{/* Critical badges */}
			{isCritical && (
				<div className="absolute top-2 right-2 bg-yellow-500 text-white text-xs font-bold px-2 py-1 rounded animate-pulse">
					CRITICAL!
				</div>
			)}
			{isCriticalFail && (
				<div className="absolute top-2 right-2 bg-red-600 text-white text-xs font-bold px-2 py-1 rounded animate-pulse">
					CRITICAL FAIL!
				</div>
			)}

			<div className="flex items-start gap-3">
				{/* Icon */}
				<div className={`
					shrink-0 w-10 h-10 rounded-full
					bg-linear-to-br ${getRollColor(roll.roll_type)}
					flex items-center justify-center text-white
					shadow-md
				`}>
					{getRollIcon(roll.roll_type)}
				</div>

				{/* Content */}
				<div className="flex-1 min-w-0">
					{/* Header */}
					<div className="flex items-center gap-2 mb-1">
						<span className="font-bold text-gray-900">
							{roll.npc_name}
						</span>
						<span className="text-gray-500">rolled</span>
						<span className={`
							text-2xl font-bold
							${isCritical ? 'text-yellow-600' :
								isCriticalFail ? 'text-red-600' :
									'text-purple-700'}
						`}>
							{roll.result}
						</span>
					</div>

					{/* Roll type and context */}
					<div className="text-sm text-gray-600 mb-2">
						<span className="font-medium">{formatRollType(roll.roll_type)}</span>
						{roll.context && (
							<>
								<span className="mx-1">•</span>
								<span className="italic">{roll.context}</span>
							</>
						)}
						{roll.target_name && (
							<>
								<span className="mx-1">vs</span>
								<span className="font-medium text-gray-800">{roll.target_name}</span>
							</>
						)}
					</div>

					{/* Breakdown */}
					<div className="text-xs font-mono bg-white/70 rounded px-2 py-1 inline-block">
						{roll.breakdown}
					</div>

					{/* Individual dice rolls if multiple */}
					{roll.rolls.length > 1 && (
						<div className="flex gap-1 mt-2">
							{roll.rolls.map((die, idx) => (
								<div
									key={idx}
									className="w-6 h-6 flex items-center justify-center bg-white rounded shadow-sm text-xs font-bold text-gray-700"
								>
									{die}
								</div>
							))}
							{roll.modifier !== 0 && (
								<div className="flex items-center text-xs text-gray-600 ml-1">
									{roll.modifier > 0 ? '+' : ''}{roll.modifier}
								</div>
							)}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}

// Add CSS animation
const styles = `
@keyframes bounce-in {
	0% {
		opacity: 0;
		transform: scale(0.3) translateY(-20px);
	}
	50% {
		transform: scale(1.05);
	}
	70% {
		transform: scale(0.9);
	}
	100% {
		opacity: 1;
		transform: scale(1) translateY(0);
	}
}

.animate-bounce-in {
	animation: bounce-in 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}
`;

// Inject styles
if (typeof document !== 'undefined') {
	const styleSheet = document.createElement('style');
	styleSheet.textContent = styles;
	document.head.appendChild(styleSheet);
}
