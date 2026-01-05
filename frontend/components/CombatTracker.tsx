"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { apiClient } from "@/lib/api-client";
import {
	Heart,
	Shield,
	SkipForward,
	Swords,
	Target,
	Zap
} from "lucide-react";
import { useEffect, useState } from "react";

interface CombatParticipant {
	character_id?: string;
	name: string;
	initiative: number;
	hp_current: number;
	hp_max: number;
	ac: number;
	is_enemy: boolean;
	conditions?: string[];
}

interface CombatLogEntry {
	round: number;
	turn: number;
	actor: string;
	action: string;
	target?: string;
	result?: string;
	damage?: number;
	timestamp: string;
}

interface CombatStatus {
	combat_id: string;
	session_id: string;
	is_active: boolean;
	current_turn: number;
	round_number: number;
	participants: CombatParticipant[];
	turn_order: number[] | null;
	combat_log: CombatLogEntry[];
	current_participant?: CombatParticipant;
}

interface CombatTrackerProps {
	sessionId: string;
	characterId: string;
	onCombatEnd?: () => void;
}

export function CombatTracker({
	sessionId,
	characterId,
	onCombatEnd,
}: CombatTrackerProps) {
	const [combatStatus, setCombatStatus] = useState<CombatStatus | null>(null);
	const [loading, setLoading] = useState(false);
	const [actionDialogOpen, setActionDialogOpen] = useState(false);
	const [damageDialogOpen, setDamageDialogOpen] = useState(false);
	const [selectedAction, setSelectedAction] = useState<string>("");
	const [selectedTarget, setSelectedTarget] = useState<number | null>(null);
	const [damageAmount, setDamageAmount] = useState<string>("");
	const [actionNotes, setActionNotes] = useState<string>("");

	useEffect(() => {
		if (combatStatus?.combat_id) {
			// Poll for combat status every 2 seconds
			const interval = setInterval(() => {
				fetchCombatStatus(combatStatus.combat_id);
			}, 2000);
			return () => clearInterval(interval);
		}
	}, [combatStatus?.combat_id]);

	const startCombat = async (participants: CombatParticipant[]) => {
		setLoading(true);
		try {
			const response = await apiClient.post('/api/combat/start', {
				session_id: sessionId,
				participants,
			});
			const data = await response.json();
			setCombatStatus(data);
		} catch (error) {
			console.error("Failed to start combat:", error);
		} finally {
			setLoading(false);
		}
	};

	const fetchCombatStatus = async (combatId: string) => {
		try {
			const response = await apiClient.get(`/api/combat/${combatId}/status`);
			const data = await response.json();
			setCombatStatus(data);
		} catch (error) {
			console.error("Failed to fetch combat status:", error);
		}
	};

	const performAction = async (
		actionType: string,
		targetIndex?: number,
		damage?: number,
		notes?: string
	) => {
		if (!combatStatus) return;

		setLoading(true);
		try {
			const response = await apiClient.post(
				`/api/combat/${combatStatus.combat_id}/action`,
				{
					action_type: actionType,
					target_index: targetIndex,
					damage,
					notes,
				}
			);
			const data = await response.json();
			await fetchCombatStatus(combatStatus.combat_id);
		} catch (error) {
			console.error("Failed to perform action:", error);
		} finally {
			setLoading(false);
			setActionDialogOpen(false);
			setDamageDialogOpen(false);
			setSelectedAction("");
			setSelectedTarget(null);
			setDamageAmount("");
			setActionNotes("");
		}
	};

	const updateParticipantHP = async (
		participantIndex: number,
		newHP: number
	) => {
		if (!combatStatus) return;

		try {
			await apiClient.patch(
				`/api/combat/${combatStatus.combat_id}/participants/${participantIndex}/hp`,
				{ hp_current: newHP }
			);
			await fetchCombatStatus(combatStatus.combat_id);
		} catch (error) {
			console.error("Failed to update HP:", error);
		}
	};

	const endCombat = async () => {
		if (!combatStatus) return;

		setLoading(true);
		try {
			const response = await apiClient.post(`/api/combat/${combatStatus.combat_id}/end`);
			const data = await response.json();
			setCombatStatus(null);
			if (onCombatEnd) onCombatEnd();
		} catch (error) {
			console.error("Failed to end combat:", error);
		} finally {
			setLoading(false);
		}
	};

	const openActionDialog = (action: string) => {
		setSelectedAction(action);
		setActionDialogOpen(true);
	};

	const openDamageDialog = (targetIndex: number) => {
		setSelectedTarget(targetIndex);
		setDamageDialogOpen(true);
	};

	const handleActionSubmit = () => {
		if (selectedAction === "attack" && selectedTarget !== null) {
			performAction("attack", selectedTarget, undefined, actionNotes);
		} else if (selectedAction !== "") {
			performAction(selectedAction, undefined, undefined, actionNotes);
		}
	};

	const handleDamageSubmit = () => {
		if (selectedTarget !== null && damageAmount) {
			const damage = parseInt(damageAmount);
			if (!isNaN(damage)) {
				const participant = combatStatus?.participants[selectedTarget];
				if (participant) {
					const newHP = Math.max(0, participant.hp_current - damage);
					updateParticipantHP(selectedTarget, newHP);
				}
			}
		}
	};

	const getHPColor = (current: number, max: number) => {
		const percentage = (current / max) * 100;
		if (percentage > 50) return "bg-green-500";
		if (percentage > 25) return "bg-yellow-500";
		return "bg-red-500";
	};

	const isPlayerTurn =
		combatStatus?.current_participant?.character_id === characterId;

	if (!combatStatus) {
		return (
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Swords className="w-5 h-5" />
						Combat Tracker
					</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="text-center py-8">
						<p className="text-muted-foreground mb-4">No active combat</p>
						<Button
							onClick={() =>
								startCombat([
									{
										character_id: characterId,
										name: "Player",
										initiative: 0,
										hp_current: 100,
										hp_max: 100,
										ac: 15,
										is_enemy: false,
									},
								])
							}
						>
							Start Combat (Demo)
						</Button>
					</div>
				</CardContent>
			</Card>
		);
	}

	return (
		<div className="space-y-4">
			{/* Combat Header */}
			<Card>
				<CardHeader>
					<div className="flex items-center justify-between">
						<CardTitle className="flex items-center gap-2">
							<Swords className="w-5 h-5" />
							Combat - Round {combatStatus.round_number}
						</CardTitle>
						<Button variant="destructive" onClick={endCombat} disabled={loading}>
							End Combat
						</Button>
					</div>
				</CardHeader>
			</Card>

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
				{/* Turn Order */}
				<Card className="lg:col-span-2">
					<CardHeader>
						<CardTitle className="text-lg">Turn Order</CardTitle>
					</CardHeader>
					<CardContent>
						<ScrollArea className="h-100">
							<div className="space-y-3">
								{combatStatus.turn_order?.map((index) => {
									const participant = combatStatus.participants[index];
									const isCurrentTurn = combatStatus.current_turn === index;
									const hpPercentage =
										(participant.hp_current / participant.hp_max) * 100;

									return (
										<div
											key={index}
											className={`p-4 rounded-lg border-2 transition-all ${isCurrentTurn
												? "border-yellow-500 bg-yellow-50 dark:bg-yellow-950"
												: "border-border"
												}`}
										>
											<div className="flex items-start justify-between mb-2">
												<div className="flex items-center gap-2">
													{participant.is_enemy ? (
														<Target className="w-5 h-5 text-red-500" />
													) : (
														<Shield className="w-5 h-5 text-blue-500" />
													)}
													<div>
														<p className="font-semibold">{participant.name}</p>
														<div className="flex items-center gap-2 text-sm text-muted-foreground">
															<span>Initiative: {participant.initiative}</span>
															<span>•</span>
															<span>AC: {participant.ac}</span>
														</div>
													</div>
												</div>
												{isCurrentTurn && (
													<Badge variant="default" className="animate-pulse">
														<Zap className="w-3 h-3 mr-1" />
														Active
													</Badge>
												)}
											</div>

											{/* HP Bar */}
											<div className="mb-2">
												<div className="flex justify-between text-sm mb-1">
													<span className="text-muted-foreground">HP</span>
													<span className="font-medium">
														{participant.hp_current} / {participant.hp_max}
													</span>
												</div>
												<Progress
													value={hpPercentage}
													className={getHPColor(
														participant.hp_current,
														participant.hp_max
													)}
												/>
											</div>

											{/* Conditions */}
											{participant.conditions && participant.conditions.length > 0 && (
												<div className="flex flex-wrap gap-1 mb-2">
													{participant.conditions.map((condition, i) => (
														<Badge key={i} variant="outline" className="text-xs">
															{condition}
														</Badge>
													))}
												</div>
											)}

											{/* Action Buttons */}
											{isCurrentTurn && isPlayerTurn && (
												<div className="grid grid-cols-3 gap-2 mt-3">
													<Button
														size="sm"
														onClick={() => openActionDialog("attack")}
														disabled={loading}
													>
														<Swords className="w-3 h-3 mr-1" />
														Attack
													</Button>
													<Button
														size="sm"
														variant="secondary"
														onClick={() => openActionDialog("dodge")}
														disabled={loading}
													>
														<Shield className="w-3 h-3 mr-1" />
														Dodge
													</Button>
													<Button
														size="sm"
														variant="outline"
														onClick={() => performAction("end_turn")}
														disabled={loading}
													>
														<SkipForward className="w-3 h-3 mr-1" />
														End Turn
													</Button>
												</div>
											)}

											{/* Quick Damage Button */}
											{!participant.is_enemy && (
												<Button
													size="sm"
													variant="ghost"
													className="w-full mt-2"
													onClick={() => openDamageDialog(index)}
												>
													<Heart className="w-3 h-3 mr-1" />
													Apply Damage/Healing
												</Button>
											)}
										</div>
									);
								})}
							</div>
						</ScrollArea>
					</CardContent>
				</Card>

				{/* Combat Log */}
				<Card>
					<CardHeader>
						<CardTitle className="text-lg">Combat Log</CardTitle>
					</CardHeader>
					<CardContent>
						<ScrollArea className="h-100">
							<div className="space-y-2">
								{combatStatus.combat_log
									.slice()
									.reverse()
									.map((entry, index) => (
										<div
											key={index}
											className="text-sm p-2 rounded bg-muted/50"
										>
											<div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
												<span>Round {entry.round}</span>
												<span>•</span>
												<span>Turn {entry.turn + 1}</span>
											</div>
											<p className="font-medium">{entry.actor}</p>
											<p>{entry.action}</p>
											{entry.target && (
												<p className="text-muted-foreground">Target: {entry.target}</p>
											)}
											{entry.result && (
												<p
													className={
														entry.result.includes("hit")
															? "text-green-600"
															: "text-red-600"
													}
												>
													{entry.result}
												</p>
											)}
											{entry.damage && (
												<p className="text-red-600 font-semibold">
													{entry.damage} damage
												</p>
											)}
										</div>
									))}
							</div>
						</ScrollArea>
					</CardContent>
				</Card>
			</div>

			{/* Action Dialog */}
			<Dialog open={actionDialogOpen} onOpenChange={setActionDialogOpen}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>
							{selectedAction === "attack" ? "Attack" : selectedAction}
						</DialogTitle>
						<DialogDescription>
							{selectedAction === "attack"
								? "Select a target to attack"
								: `Perform ${selectedAction} action`}
						</DialogDescription>
					</DialogHeader>

					{selectedAction === "attack" && (
						<div className="space-y-4">
							<Select
								value={selectedTarget?.toString()}
								onValueChange={(value) => setSelectedTarget(parseInt(value))}
							>
								<SelectTrigger>
									<SelectValue placeholder="Select target" />
								</SelectTrigger>
								<SelectContent>
									{combatStatus.participants.map((p, index) => (
										<SelectItem key={index} value={index.toString()}>
											{p.name} (AC: {p.ac}, HP: {p.hp_current}/{p.hp_max})
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
					)}

					<div>
						<label className="text-sm font-medium">Notes (optional)</label>
						<Input
							value={actionNotes}
							onChange={(e) => setActionNotes(e.target.value)}
							placeholder="Add notes about this action..."
						/>
					</div>

					<DialogFooter>
						<Button variant="outline" onClick={() => setActionDialogOpen(false)}>
							Cancel
						</Button>
						<Button onClick={handleActionSubmit} disabled={loading}>
							Perform Action
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>

			{/* Damage Dialog */}
			<Dialog open={damageDialogOpen} onOpenChange={setDamageDialogOpen}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>Apply Damage/Healing</DialogTitle>
						<DialogDescription>
							Enter damage amount (positive) or healing (negative)
						</DialogDescription>
					</DialogHeader>

					<div>
						<label className="text-sm font-medium">Amount</label>
						<Input
							type="number"
							value={damageAmount}
							onChange={(e) => setDamageAmount(e.target.value)}
							placeholder="e.g., 10 for damage, -10 for healing"
						/>
					</div>

					<DialogFooter>
						<Button variant="outline" onClick={() => setDamageDialogOpen(false)}>
							Cancel
						</Button>
						<Button onClick={handleDamageSubmit} disabled={loading}>
							Apply
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</div>
	);
}
