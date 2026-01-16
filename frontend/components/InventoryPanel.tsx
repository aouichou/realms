"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Beaker, Box, Grid3x3, List, Package, ScrollText, Shield, Sword } from "lucide-react";
import { useEffect, useState } from "react";

interface Item {
	id: string;
	name: string;
	item_type: "weapon" | "armor" | "consumable" | "quest" | "misc";
	weight: number;
	value: number;
	quantity: number;
	equipped: boolean;
	properties: Record<string, any>;
}

interface InventoryData {
	items: Item[];
	current_weight: number;
	carrying_capacity: number;
	weight_percentage: number;
}

interface InventoryPanelProps {
	characterId: string;
}

const ITEM_ICONS = {
	weapon: Sword,
	armor: Shield,
	consumable: Beaker,
	quest: ScrollText,
	misc: Box,
};

const ITEM_COLORS = {
	weapon: "bg-red-500/10 border-red-500",
	armor: "bg-blue-500/10 border-blue-500",
	consumable: "bg-green-500/10 border-green-500",
	quest: "bg-yellow-500/10 border-yellow-500",
	misc: "bg-gray-500/10 border-gray-500",
};

export function InventoryPanel({ characterId }: InventoryPanelProps) {
	const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
	const [inventory, setInventory] = useState<InventoryData | null>(null);
	const [loading, setLoading] = useState(true);
	const [selectedItem, setSelectedItem] = useState<Item | null>(null);
	const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
	const [filterType, setFilterType] = useState<string>("all");
	const [sortBy, setSortBy] = useState<string>("name");

	useEffect(() => {
		fetchInventory();
	}, [characterId, filterType]);

	const fetchInventory = async () => {
		try {
			const params = new URLSearchParams();
			if (filterType !== "all") {
				params.append("item_type", filterType);
			}

			const response = await fetch(
				`${API_URL}/api/v1/characters/${characterId}/inventory?${params}`
			);
			const data = await response.json();
			setInventory(data);
		} catch (error) {
			console.error("Failed to fetch inventory:", error);
		} finally {
			setLoading(false);
		}
	};

	const toggleEquip = async (itemId: string) => {
		try {
			await fetch(
				`${API_URL}/api/v1/characters/${characterId}/inventory/${itemId}/equip`,
				{ method: "PATCH" }
			);
			fetchInventory();
		} catch (error) {
			console.error("Failed to toggle equip:", error);
		}
	};

	const deleteItem = async (itemId: string) => {
		try {
			await fetch(
				`${API_URL}/api/v1/characters/${characterId}/inventory/${itemId}`,
				{ method: "DELETE" }
			);
			setSelectedItem(null);
			fetchInventory();
		} catch (error) {
			console.error("Failed to delete item:", error);
		}
	};

	const sortedItems = (inventory?.items || []).slice().sort((a, b) => {
		switch (sortBy) {
			case "name":
				return a.name.localeCompare(b.name);
			case "type":
				return a.item_type.localeCompare(b.item_type);
			case "weight":
				return a.weight - b.weight;
			case "value":
				return b.value - a.value;
			default:
				return 0;
		}
	}) || [];

	const weightPercentage = inventory?.weight_percentage || 0;
	const weightColor =
		weightPercentage < 75 ? "bg-green-500" : weightPercentage < 100 ? "bg-yellow-500" : "bg-red-500";

	if (loading) {
		return (
			<Card>
				<CardHeader>
					<CardTitle>Inventory</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="flex items-center justify-center h-64">
						<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
					</div>
				</CardContent>
			</Card>
		);
	}

	return (
		<>
			<Card>
				<CardHeader>
					<div className="flex items-center justify-between">
						<CardTitle className="flex items-center gap-2">
							<Package className="w-5 h-5" />
							Inventory
						</CardTitle>
						<div className="flex gap-2">
							<Button
								variant={viewMode === "grid" ? "default" : "outline"}
								size="sm"
								onClick={() => setViewMode("grid")}
							>
								<Grid3x3 className="w-4 h-4" />
							</Button>
							<Button
								variant={viewMode === "list" ? "default" : "outline"}
								size="sm"
								onClick={() => setViewMode("list")}
							>
								<List className="w-4 h-4" />
							</Button>
						</div>
					</div>

					{/* Weight Capacity Bar */}
					<div className="space-y-2 mt-4">
						<div className="flex justify-between text-sm">
							<span>Carrying Capacity</span>
							<span className="font-medium">
								{inventory?.current_weight.toFixed(1)} / {inventory?.carrying_capacity} lbs
							</span>
						</div>
						<Progress value={weightPercentage} className={weightColor} />
					</div>

					{/* Filters */}
					<div className="flex gap-2 mt-4">
						<Select value={filterType} onValueChange={setFilterType}>
							<SelectTrigger className="w-37.5">
								<SelectValue placeholder="Filter by type" />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="all">All Items</SelectItem>
								<SelectItem value="weapon">Weapons</SelectItem>
								<SelectItem value="armor">Armor</SelectItem>
								<SelectItem value="consumable">Consumables</SelectItem>
								<SelectItem value="quest">Quest Items</SelectItem>
								<SelectItem value="misc">Miscellaneous</SelectItem>
							</SelectContent>
						</Select>

						<Select value={sortBy} onValueChange={setSortBy}>
							<SelectTrigger className="w-37.5">
								<SelectValue placeholder="Sort by" />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="name">Name (A-Z)</SelectItem>
								<SelectItem value="type">Type</SelectItem>
								<SelectItem value="weight">Weight (Low-High)</SelectItem>
								<SelectItem value="value">Value (High-Low)</SelectItem>
							</SelectContent>
						</Select>
					</div>
				</CardHeader>

				<CardContent>
					<ScrollArea className="h-100">
						{sortedItems.length === 0 ? (
							<div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
								<Package className="w-12 h-12 mb-2" />
								<p>No items in inventory</p>
							</div>
						) : viewMode === "grid" ? (
							<div className="grid grid-cols-4 gap-3">
								{sortedItems.map((item) => {
									const Icon = ITEM_ICONS[item.item_type];
									const colorClass = ITEM_COLORS[item.item_type];

									return (
										<Card
											key={item.id}
											className={`cursor-pointer hover:shadow-lg transition-shadow ${item.equipped ? "ring-2 ring-green-500" : ""
												} ${colorClass}`}
											onClick={() => setSelectedItem(item)}
										>
											<CardContent className="p-4">
												<div className="flex flex-col items-center text-center space-y-2">
													<Icon className="w-8 h-8" />
													<div className="space-y-1">
														<p className="font-medium text-sm line-clamp-2">{item.name}</p>
														{item.quantity > 1 && (
															<Badge variant="secondary" className="text-xs">
																x{item.quantity}
															</Badge>
														)}
														{item.equipped && (
															<Badge variant="default" className="text-xs bg-green-500">
																Equipped
															</Badge>
														)}
													</div>
													<div className="text-xs text-muted-foreground">
														{item.weight} lb
													</div>
												</div>
											</CardContent>
										</Card>
									);
								})}
							</div>
						) : (
							<div className="space-y-2">
								{sortedItems.map((item) => {
									const Icon = ITEM_ICONS[item.item_type];
									const colorClass = ITEM_COLORS[item.item_type];

									return (
										<Card
											key={item.id}
											className={`cursor-pointer hover:shadow-lg transition-shadow ${item.equipped ? "ring-2 ring-green-500" : ""
												} ${colorClass}`}
											onClick={() => setSelectedItem(item)}
										>
											<CardContent className="p-3">
												<div className="flex items-center justify-between">
													<div className="flex items-center gap-3">
														<Icon className="w-5 h-5" />
														<div>
															<p className="font-medium">{item.name}</p>
															<p className="text-xs text-muted-foreground">
																{item.item_type} • {item.weight} lb • {item.value} gp
															</p>
														</div>
													</div>
													<div className="flex items-center gap-2">
														{item.quantity > 1 && (
															<Badge variant="secondary">x{item.quantity}</Badge>
														)}
														{item.equipped && (
															<Badge variant="default" className="bg-green-500">
																Equipped
															</Badge>
														)}
													</div>
												</div>
											</CardContent>
										</Card>
									);
								})}
							</div>
						)}
					</ScrollArea>
				</CardContent>
			</Card>

			{/* Item Details Modal */}
			<Dialog open={!!selectedItem} onOpenChange={() => setSelectedItem(null)}>
				<DialogContent>
					<DialogHeader>
						<DialogTitle>{selectedItem?.name}</DialogTitle>
						<DialogDescription>
							{selectedItem ? selectedItem.item_type.charAt(0).toUpperCase() + selectedItem.item_type.slice(1) : ''}
						</DialogDescription>
					</DialogHeader>

					{selectedItem && (
						<div className="space-y-4">
							<div className="grid grid-cols-2 gap-4">
								<div>
									<p className="text-sm text-muted-foreground">Weight</p>
									<p className="font-medium">{selectedItem.weight} lbs</p>
								</div>
								<div>
									<p className="text-sm text-muted-foreground">Value</p>
									<p className="font-medium">{selectedItem.value} gp</p>
								</div>
								<div>
									<p className="text-sm text-muted-foreground">Quantity</p>
									<p className="font-medium">{selectedItem.quantity}</p>
								</div>
								<div>
									<p className="text-sm text-muted-foreground">Status</p>
									<p className="font-medium">
										{selectedItem.equipped ? "Equipped" : "In Inventory"}
									</p>
								</div>
							</div>

							{selectedItem.properties && Object.keys(selectedItem.properties).length > 0 && (
								<div>
									<p className="text-sm text-muted-foreground mb-2">Properties</p>
									<div className="space-y-1">
										{Object.entries(selectedItem.properties).map(([key, value]) => (
											<div key={key} className="flex justify-between text-sm">
												<span className="capitalize">{key.replace(/_/g, " ")}:</span>
												<span className="font-medium">{JSON.stringify(value)}</span>
											</div>
										))}
									</div>
								</div>
							)}

							<div className="flex gap-2 pt-4">
								<Button
									onClick={() => {
										toggleEquip(selectedItem.id);
										setSelectedItem(null);
									}}
									className="flex-1"
								>
									{selectedItem.equipped ? "Unequip" : "Equip"}
								</Button>
								<Button
									variant="destructive"
									onClick={() => deleteItem(selectedItem.id)}
									className="flex-1"
								>
									Drop Item
								</Button>
							</div>
						</div>
					)}
				</DialogContent>
			</Dialog>
		</>
	);
}
