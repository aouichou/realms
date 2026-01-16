"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { SpellCard } from "./SpellCard";
import { SpellDetail } from "./SpellDetail";
import { SpellFilters } from "./SpellFilters";

export interface Spell {
	id: string;
	name: string;
	level: number;
	school: string;
	casting_time: string;
	range: string;
	duration: string;
	verbal: boolean;
	somatic: boolean;
	material: string | null;
	description: string;
	is_concentration: boolean;
	is_ritual: boolean;
	damage_dice: string | null;
	damage_type: string | null;
	save_ability: string | null;
	available_to_classes: Record<string, boolean>;
	created_at: string;
}

export interface SpellFiltersState {
	level: number | null;
	school: string | null;
	characterClass: string | null;
	concentration: boolean | null;
	ritual: boolean | null;
}

interface SpellBrowserProps {
	onSpellSelect?: (spell: Spell) => void;
	selectedSpells?: Set<string>;
	filterByClass?: string;
}

export function SpellBrowser({ onSpellSelect, selectedSpells, filterByClass }: SpellBrowserProps) {
	const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
	const [spells, setSpells] = useState<Spell[]>([]);
	const [totalSpells, setTotalSpells] = useState(0);
	const [page, setPage] = useState(1);
	const [loading, setLoading] = useState(true);
	const [search, setSearch] = useState("");
	const [selectedSpell, setSelectedSpell] = useState<Spell | null>(null);
	const [filters, setFilters] = useState<SpellFiltersState>({
		level: null,
		school: null,
		characterClass: filterByClass || null,
		concentration: null,
		ritual: null,
	});

	const debouncedSearch = useDebounce(search, 300);
	const pageSize = 20;

	const fetchSpells = useCallback(async () => {
		setLoading(true);
		try {
			const params = new URLSearchParams({
				page: page.toString(),
				page_size: pageSize.toString(),
			});

			if (debouncedSearch) params.append("search", debouncedSearch);
			if (filters.level !== null) params.append("level", filters.level.toString());
			if (filters.school) params.append("school", filters.school);
			if (filters.characterClass) params.append("character_class", filters.characterClass);
			if (filters.concentration !== null) params.append("concentration", filters.concentration.toString());
			if (filters.ritual !== null) params.append("ritual", filters.ritual.toString());

			const response = await fetch(`${API_URL}/api/v1/spells?${params.toString()}`);
			const data = await response.json();

			setSpells(data.spells);
			setTotalSpells(data.total);
		} catch (error) {
			console.error("Failed to fetch spells:", error);
		} finally {
			setLoading(false);
		}
	}, [page, debouncedSearch, filters]);

	useEffect(() => {
		fetchSpells();
	}, [fetchSpells]);

	useEffect(() => {
		// Reset to page 1 when filters change
		setPage(1);
	}, [debouncedSearch, filters]);

	const handleFilterChange = (newFilters: Partial<SpellFiltersState>) => {
		setFilters(prev => ({ ...prev, ...newFilters }));
	};

	const handleCardClick = (spell: Spell) => {
		setSelectedSpell(spell);
	};

	const handleSpellSelect = (spell: Spell) => {
		if (onSpellSelect) {
			onSpellSelect(spell);
		}
	};

	const totalPages = Math.ceil(totalSpells / pageSize);
	const canGoNext = page < totalPages;
	const canGoPrev = page > 1;

	return (
		<div className="flex h-full gap-4">
			{/* Filters Sidebar */}
			<div className="w-64 shrink-0">
				<SpellFilters
					filters={filters}
					onFilterChange={handleFilterChange}
				/>
			</div>

			{/* Spells List */}
			<div className="flex-1 flex flex-col">
				{/* Search Bar */}
				<div className="mb-4">
					<Input
						type="text"
						placeholder="Search spells..."
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						className="w-full"
					/>
				</div>

				{/* Results Count */}
				<div className="text-sm text-muted-foreground mb-2">
					{loading ? "Loading..." : `${totalSpells} spell${totalSpells !== 1 ? 's' : ''} found`}
				</div>

				{/* Spells Grid */}
				<ScrollArea className="flex-1">
					<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-4">
						{spells.map((spell) => (
							<SpellCard
								key={spell.id}
								spell={spell}
								onClick={() => handleCardClick(spell)}
								onSelect={onSpellSelect ? () => handleSpellSelect(spell) : undefined}
								isSelected={selectedSpells?.has(spell.id)}
							/>
						))}
					</div>

					{!loading && spells.length === 0 && (
						<div className="text-center py-8 text-muted-foreground">
							No spells found matching your criteria
						</div>
					)}
				</ScrollArea>

				{/* Pagination */}
				{totalPages > 1 && (
					<div className="flex items-center justify-between mt-4 pt-4 border-t">
						<Button
							type="button"
							variant="outline"
							size="sm"
							onClick={() => setPage(p => p - 1)}
							disabled={!canGoPrev}
						>
							<ChevronLeft className="h-4 w-4 mr-1" />
							Previous
						</Button>

						<div className="text-sm text-muted-foreground">
							Page {page} of {totalPages}
						</div>

						<Button
							type="button"
							variant="outline"
							size="sm"
							onClick={() => setPage(p => p + 1)}
							disabled={!canGoNext}
						>
							Next
							<ChevronRight className="h-4 w-4 ml-1" />
						</Button>
					</div>
				)}
			</div>

			{/* Spell Detail Modal */}
			{selectedSpell && (
				<SpellDetail
					spell={selectedSpell}
					open={!!selectedSpell}
					onClose={() => setSelectedSpell(null)}
					onSelect={onSpellSelect ? () => handleSpellSelect(selectedSpell) : undefined}
					isSelected={selectedSpells?.has(selectedSpell.id)}
				/>
			)}
		</div>
	);
}
