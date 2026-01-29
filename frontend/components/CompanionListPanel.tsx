"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiClient } from "@/lib/api-client";
import { Eye, EyeOff, Shield, Users } from "lucide-react";
import Image from "next/image";
import { useEffect, useState } from "react";

interface Companion {
	id: string;
	name: string;
	creature_name: string;
	personality: string;
	relationship_status: string;
	loyalty: number;
	hp: number;
	max_hp: number;
	ac: number;
	is_active: boolean;
	is_alive: boolean;
	avatar_url?: string;
	goals?: string;
	background?: string;
}

interface CompanionListPanelProps {
	characterId: string;
	onCompanionToggle?: (companionId: string, isActive: boolean) => void;
}

const RELATIONSHIP_COLORS = {
	just_met: { badge: "bg-gray-500/20 text-gray-300", text: "Just Met" },
	ally: { badge: "bg-blue-500/20 text-blue-300", text: "Ally" },
	friend: { badge: "bg-green-500/20 text-green-300", text: "Friend" },
	trusted: { badge: "bg-purple-500/20 text-purple-300", text: "Trusted" },
	suspicious: { badge: "bg-red-500/20 text-red-300", text: "Suspicious" },
};

export function CompanionListPanel({ characterId, onCompanionToggle }: CompanionListPanelProps) {
	const [companions, setCompanions] = useState<Companion[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		fetchCompanions();
	}, [characterId]);

	const fetchCompanions = async () => {
		try {
			setLoading(true);
			setError(null);

			const response = await apiClient.get(`/api/v1/companions/characters/${characterId}/companions`);

			if (response.ok) {
				const data = await response.json();
				setCompanions(data);
			} else {
				setError("Failed to load companions");
			}
		} catch (err) {
			console.error("Error fetching companions:", err);
			setError("Failed to load companions");
		} finally {
			setLoading(false);
		}
	};

	const toggleCompanionActive = async (companionId: string, currentActive: boolean) => {
		try {
			const response = await apiClient.patch(
				`/api/v1/companions/${companionId}/active`,
				{ is_active: !currentActive }
			);

			if (response.ok) {
				// Update local state
				setCompanions(prev =>
					prev.map(c =>
						c.id === companionId ? { ...c, is_active: !currentActive } : c
					)
				);

				// Notify parent
				onCompanionToggle?.(companionId, !currentActive);
			}
		} catch (err) {
			console.error("Error toggling companion:", err);
		}
	};

	const getLoyaltyColor = (loyalty: number) => {
		if (loyalty >= 80) return "text-green-400";
		if (loyalty >= 60) return "text-blue-400";
		if (loyalty >= 40) return "text-yellow-400";
		if (loyalty >= 20) return "text-orange-400";
		return "text-red-400";
	};

	const getLoyaltyBarColor = (loyalty: number) => {
		if (loyalty >= 80) return "bg-green-500";
		if (loyalty >= 60) return "bg-blue-500";
		if (loyalty >= 40) return "bg-yellow-500";
		if (loyalty >= 20) return "bg-orange-500";
		return "bg-red-500";
	};

	const getHPColor = (hp: number, maxHp: number) => {
		const percent = (hp / maxHp) * 100;
		if (percent >= 75) return "bg-green-500";
		if (percent >= 50) return "bg-yellow-500";
		if (percent >= 25) return "bg-orange-500";
		return "bg-red-500";
	};

	if (loading) {
		return (
			<Card className="bg-slate-900/50 border-slate-700">
				<CardHeader>
					<div className="flex items-center gap-2">
						<Users className="w-5 h-5 text-teal-400" />
						<h3 className="text-lg font-display text-white">Companions</h3>
					</div>
				</CardHeader>
				<CardContent>
					<div className="flex items-center justify-center p-8">
						<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-400"></div>
					</div>
				</CardContent>
			</Card>
		);
	}

	if (error) {
		return (
			<Card className="bg-slate-900/50 border-slate-700">
				<CardHeader>
					<div className="flex items-center gap-2">
						<Users className="w-5 h-5 text-teal-400" />
						<h3 className="text-lg font-display text-white">Companions</h3>
					</div>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-red-400">{error}</p>
					<Button
						onClick={fetchCompanions}
						size="sm"
						className="mt-2 bg-teal-600 hover:bg-teal-700"
					>
						Retry
					</Button>
				</CardContent>
			</Card>
		);
	}

	if (companions.length === 0) {
		return (
			<Card className="bg-slate-900/50 border-slate-700">
				<CardHeader>
					<div className="flex items-center gap-2">
						<Users className="w-5 h-5 text-teal-400" />
						<h3 className="text-lg font-display text-white">Companions</h3>
					</div>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-gray-400 text-center py-4">
						No companions yet. Ask the DM to introduce a companion to join your adventure!
					</p>
				</CardContent>
			</Card>
		);
	}

	return (
		<Card className="bg-slate-900/50 border-slate-700">
			<CardHeader>
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-2">
						<Users className="w-5 h-5 text-teal-400" />
						<h3 className="text-lg font-display text-white">Companions</h3>
						<Badge variant="outline" className="bg-teal-500/20 text-teal-300 border-teal-500/30">
							{companions.filter(c => c.is_active).length} Active
						</Badge>
					</div>
				</div>
			</CardHeader>
			<CardContent>
				<ScrollArea className="h-[400px] pr-4">
					<div className="space-y-3">
						{companions.map((companion) => (
							<div
								key={companion.id}
								className={`
									relative p-3 rounded-lg border transition-all
									${companion.is_active
										? "bg-teal-900/20 border-teal-500/30 shadow-lg shadow-teal-500/10"
										: "bg-slate-800/30 border-slate-700/50"
									}
									${!companion.is_alive && "opacity-50"}
								`}
							>
								{/* Header with Avatar and Name */}
								<div className="flex items-start gap-3 mb-2">
									{/* Avatar */}
									<div className="relative w-12 h-12 rounded-lg overflow-hidden border-2 border-teal-500/30 flex-shrink-0">
										{companion.avatar_url ? (
											<Image
												src={companion.avatar_url}
												alt={companion.name}
												fill
												className="object-cover"
											/>
										) : (
											<div className="w-full h-full bg-gradient-to-br from-teal-600 to-emerald-700 flex items-center justify-center">
												<span className="text-white text-xl font-bold">
													{companion.name.charAt(0)}
												</span>
											</div>
										)}
									</div>

									{/* Name and Info */}
									<div className="flex-1 min-w-0">
										<div className="flex items-center gap-2">
											<h4 className="font-display text-white truncate">
												{companion.name}
											</h4>
											{!companion.is_alive && (
												<Badge variant="outline" className="bg-red-500/20 text-red-300 border-red-500/30 text-xs">
													Unconscious
												</Badge>
											)}
										</div>
										<p className="text-xs text-gray-400">{companion.creature_name}</p>

										{/* Relationship Badge */}
										<Badge
											variant="outline"
											className={`mt-1 text-xs ${RELATIONSHIP_COLORS[companion.relationship_status as keyof typeof RELATIONSHIP_COLORS]?.badge || "bg-gray-500/20 text-gray-300"
												}`}
										>
											{RELATIONSHIP_COLORS[companion.relationship_status as keyof typeof RELATIONSHIP_COLORS]?.text || companion.relationship_status}
										</Badge>
									</div>

									{/* Toggle Active Button */}
									<Button
										size="sm"
										variant="ghost"
										onClick={() => toggleCompanionActive(companion.id, companion.is_active)}
										className={`
											h-8 w-8 p-0
											${companion.is_active
												? "text-teal-400 hover:text-teal-300"
												: "text-gray-500 hover:text-gray-400"
											}
										`}
										title={companion.is_active ? "Deactivate" : "Activate"}
									>
										{companion.is_active ? (
											<Eye className="w-4 h-4" />
										) : (
											<EyeOff className="w-4 h-4" />
										)}
									</Button>
								</div>

								{/* Stats */}
								<div className="space-y-2 text-xs">
									{/* HP Bar */}
									<div>
										<div className="flex items-center justify-between mb-1">
											<span className="text-gray-400">HP</span>
											<span className="text-white font-mono">
												{companion.hp} / {companion.max_hp}
											</span>
										</div>
										<div className="h-2 bg-slate-700 rounded-full overflow-hidden">
											<div
												className={`h-full transition-all ${getHPColor(companion.hp, companion.max_hp)}`}
												style={{ width: `${(companion.hp / companion.max_hp) * 100}%` }}
											/>
										</div>
									</div>

									{/* Loyalty Bar */}
									<div>
										<div className="flex items-center justify-between mb-1">
											<span className="text-gray-400">Loyalty</span>
											<span className={`font-mono font-semibold ${getLoyaltyColor(companion.loyalty)}`}>
												{companion.loyalty}%
											</span>
										</div>
										<div className="h-2 bg-slate-700 rounded-full overflow-hidden">
											<div
												className={`h-full transition-all ${getLoyaltyBarColor(companion.loyalty)}`}
												style={{ width: `${companion.loyalty}%` }}
											/>
										</div>
									</div>

									{/* AC */}
									<div className="flex items-center justify-between pt-1 border-t border-slate-700/50">
										<span className="text-gray-400 flex items-center gap-1">
											<Shield className="w-3 h-3" />
											AC
										</span>
										<span className="text-white font-mono">{companion.ac}</span>
									</div>
								</div>

								{/* Personality Snippet */}
								{companion.personality && (
									<div className="mt-2 pt-2 border-t border-slate-700/50">
										<p className="text-xs text-gray-400 italic line-clamp-2">
											"{companion.personality}"
										</p>
									</div>
								)}
							</div>
						))}
					</div>
				</ScrollArea>
			</CardContent>
		</Card>
	);
}
