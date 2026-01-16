"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle, Coins, Sparkles, Trophy } from "lucide-react";
import { useEffect, useState } from "react";

interface QuestReward {
	xp: number;
	gold: number;
	items: string[];
}

interface QuestCompleteModalProps {
	questTitle: string;
	rewards: QuestReward;
	isOpen: boolean;
	onClose: () => void;
	onClaimRewards: () => Promise<void>;
}

export function QuestCompleteModal({
	questTitle,
	rewards,
	isOpen,
	onClose,
	onClaimRewards,
}: QuestCompleteModalProps) {
	const [claiming, setClaiming] = useState(false);
	const [claimed, setClaimed] = useState(false);

	useEffect(() => {
		if (!isOpen) {
			setClaimed(false);
		}
	}, [isOpen]);

	const handleClaim = async () => {
		setClaiming(true);
		try {
			await onClaimRewards();
			setClaimed(true);
		} catch (error) {
			console.error('Failed to claim rewards:', error);
		} finally {
			setClaiming(false);
		}
	};

	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
			<Card className="max-w-md w-full bg-linear-to-b from-accent-400/20 to-primary-900 border-accent-400/30 shadow-2xl">
				<CardHeader className="text-center">
					<div className="mx-auto mb-4 w-16 h-16 bg-accent-400/20 rounded-full flex items-center justify-center">
						<Trophy className="w-10 h-10 text-accent-400" />
					</div>
					<CardTitle className="text-2xl font-display text-white">Quest Complete!</CardTitle>
					<CardDescription className="text-white/80 font-body text-lg">
						{questTitle}
					</CardDescription>
				</CardHeader>

				<CardContent className="space-y-4">
					{/* Rewards Section */}
					<div className="bg-primary-900/50 rounded-lg p-4 space-y-3">
						<div className="flex items-center gap-2 mb-2">
							<Sparkles className="w-5 h-5 text-accent-400" />
							<h3 className="font-display text-lg text-white">Rewards</h3>
						</div>

						{/* XP Reward */}
						{rewards.xp > 0 && (
							<div className="flex items-center justify-between">
								<span className="text-white/80 font-body">Experience Points</span>
								<Badge variant="secondary" className="bg-accent-400/20 text-accent-400 font-bold">
									+{rewards.xp} XP
								</Badge>
							</div>
						)}

						{/* Gold Reward */}
						{rewards.gold > 0 && (
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<Coins className="w-4 h-4 text-yellow-400" />
									<span className="text-white/80 font-body">Gold</span>
								</div>
								<Badge variant="secondary" className="bg-yellow-400/20 text-yellow-400 font-bold">
									+{rewards.gold} GP
								</Badge>
							</div>
						)}

						{/* Item Rewards */}
						{rewards.items && rewards.items.length > 0 && (
							<div className="space-y-2">
								<div className="flex items-center gap-2">
									<CheckCircle className="w-4 h-4 text-green-400" />
									<span className="text-white/80 font-body">Items</span>
								</div>
								<div className="flex flex-wrap gap-2 ml-6">
									{rewards.items.map((item, index) => (
										<Badge key={index} variant="outline" className="border-white/20 text-white font-body">
											{item}
										</Badge>
									))}
								</div>
							</div>
						)}
					</div>

					{/* Success Message */}
					{claimed && (
						<div className="bg-green-400/20 border border-green-400/30 rounded-lg p-3 text-center">
							<p className="text-green-400 font-body text-sm">
								✓ Rewards claimed successfully!
							</p>
						</div>
					)}
				</CardContent>

				<CardFooter className="flex gap-2">
					{!claimed ? (
						<>
							<Button
								variant="outline"
								onClick={onClose}
								className="flex-1 border-white/20 text-white hover:bg-white/10 font-body"
								disabled={claiming}
							>
								Close
							</Button>
							<Button
								onClick={handleClaim}
								className="flex-1 bg-accent-400 hover:bg-accent-500 text-primary-900 font-body"
								disabled={claiming}
							>
								{claiming ? 'Claiming...' : 'Claim Rewards'}
							</Button>
						</>
					) : (
						<Button
							onClick={onClose}
							className="w-full bg-accent-400 hover:bg-accent-500 text-primary-900 font-body"
						>
							Continue Adventure
						</Button>
					)}
				</CardFooter>
			</Card>
		</div>
	);
}
