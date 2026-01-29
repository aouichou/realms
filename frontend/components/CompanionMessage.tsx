import { Heart, Shield, Sparkles, Users } from 'lucide-react';
import { useEffect, useState } from 'react';

interface CompanionData {
	id: number;
	name: string;
	creature_name: string;
	personality: string;
	relationship_status: string;
	loyalty: number;
	hp: number;
	max_hp: number;
	ac: number;
	avatar_url?: string;
}

interface CompanionMessageProps {
	companion: CompanionData;
	message: string;
	showStats?: boolean;
}

export default function CompanionMessage({
	companion,
	message,
	showStats = false,
}: CompanionMessageProps) {
	const [isAnimating, setIsAnimating] = useState(true);

	useEffect(() => {
		const timer = setTimeout(() => setIsAnimating(false), 400);
		return () => clearTimeout(timer);
	}, []);

	const getRelationshipColor = (status: string) => {
		switch (status) {
			case 'trusted':
				return 'from-emerald-500 to-green-500';
			case 'friend':
				return 'from-green-500 to-teal-500';
			case 'ally':
				return 'from-teal-500 to-cyan-500';
			case 'suspicious':
				return 'from-yellow-500 to-orange-500';
			default:
				return 'from-cyan-500 to-blue-500';
		}
	};

	const getRelationshipIcon = (status: string) => {
		switch (status) {
			case 'trusted':
				return <Heart className="w-4 h-4 fill-current" />;
			case 'friend':
				return <Users className="w-4 h-4" />;
			case 'ally':
				return <Shield className="w-4 h-4" />;
			default:
				return <Sparkles className="w-4 h-4" />;
		}
	};

	const getLoyaltyColor = (loyalty: number) => {
		if (loyalty >= 80) return 'text-emerald-400';
		if (loyalty >= 60) return 'text-green-400';
		if (loyalty >= 40) return 'text-yellow-400';
		if (loyalty >= 20) return 'text-orange-400';
		return 'text-red-400';
	};

	const hpPercentage = (companion.hp / companion.max_hp) * 100;
	const getHpColor = () => {
		if (hpPercentage >= 75) return 'bg-green-500';
		if (hpPercentage >= 50) return 'bg-yellow-500';
		if (hpPercentage >= 25) return 'bg-orange-500';
		return 'bg-red-500';
	};

	return (
		<div
			className={`
				group relative
				${isAnimating ? 'animate-fade-in-up' : ''}
			`}
		>
			{/* Companion Message Container */}
			<div className="flex items-start gap-3 mb-4">
				{/* Avatar */}
				<div className="relative flex-shrink-0">
					<div
						className={`
							w-12 h-12 rounded-full
							bg-gradient-to-br ${getRelationshipColor(companion.relationship_status)}
							flex items-center justify-center
							ring-2 ring-offset-2 ring-offset-[#0a0a0a] ring-teal-500/50
							shadow-lg shadow-teal-500/20
							transition-all duration-300
							group-hover:ring-teal-400/70 group-hover:shadow-teal-400/30
						`}
					>
						{companion.avatar_url ? (
							<img
								src={companion.avatar_url}
								alt={companion.name}
								className="w-full h-full rounded-full object-cover"
							/>
						) : (
							<Users className="w-6 h-6 text-white" />
						)}
					</div>

					{/* Relationship Status Badge */}
					<div
						className={`
							absolute -bottom-1 -right-1
							w-5 h-5 rounded-full
							bg-gradient-to-br ${getRelationshipColor(companion.relationship_status)}
							flex items-center justify-center
							ring-2 ring-[#0a0a0a]
							shadow-lg
						`}
					>
						{getRelationshipIcon(companion.relationship_status)}
					</div>
				</div>

				{/* Message Content */}
				<div className="flex-1 min-w-0">
					{/* Header */}
					<div className="flex items-center gap-2 mb-1">
						<span className="font-semibold text-teal-300 text-sm">
							{companion.name}
						</span>
						<span className="text-xs text-gray-500">
							{companion.creature_name}
						</span>
						{showStats && (
							<>
								<span className="text-xs text-gray-600">•</span>
								<span className={`text-xs font-medium ${getLoyaltyColor(companion.loyalty)}`}>
									Loyalty: {companion.loyalty}%
								</span>
							</>
						)}
					</div>

					{/* Message Text */}
					<div
						className={`
							px-4 py-3 rounded-2xl rounded-tl-sm
							bg-gradient-to-br from-teal-900/40 to-emerald-900/30
							border border-teal-700/50
							shadow-lg shadow-teal-900/20
							backdrop-blur-sm
							transition-all duration-300
							hover:border-teal-600/60 hover:shadow-teal-800/30
						`}
					>
						<p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
							{message}
						</p>
					</div>

					{/* Stats Bar (Optional) */}
					{showStats && (
						<div className="mt-2 flex items-center gap-3 text-xs">
							{/* HP Bar */}
							<div className="flex items-center gap-2">
								<Heart className="w-3 h-3 text-red-400" />
								<div className="flex items-center gap-1">
									<span className="text-gray-400">{companion.hp}</span>
									<span className="text-gray-600">/</span>
									<span className="text-gray-500">{companion.max_hp}</span>
								</div>
								<div className="w-16 h-1.5 bg-gray-800 rounded-full overflow-hidden">
									<div
										className={`h-full ${getHpColor()} transition-all duration-500`}
										style={{ width: `${hpPercentage}%` }}
									/>
								</div>
							</div>

							{/* AC */}
							<div className="flex items-center gap-1.5">
								<Shield className="w-3 h-3 text-blue-400" />
								<span className="text-gray-400">{companion.ac}</span>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
