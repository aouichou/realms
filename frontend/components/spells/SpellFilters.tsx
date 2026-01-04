"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { X } from "lucide-react";
import { SpellFiltersState } from "./SpellBrowser";

interface SpellFiltersProps {
  filters: SpellFiltersState;
  onFilterChange: (filters: Partial<SpellFiltersState>) => void;
}

const SPELL_LEVELS = [
  { value: null, label: "All Levels" },
  { value: 0, label: "Cantrip" },
  { value: 1, label: "1st Level" },
  { value: 2, label: "2nd Level" },
  { value: 3, label: "3rd Level" },
  { value: 4, label: "4th Level" },
  { value: 5, label: "5th Level" },
  { value: 6, label: "6th Level" },
  { value: 7, label: "7th Level" },
  { value: 8, label: "8th Level" },
  { value: 9, label: "9th Level" },
];

const SPELL_SCHOOLS = [
  "Abjuration",
  "Conjuration",
  "Divination",
  "Enchantment",
  "Evocation",
  "Illusion",
  "Necromancy",
  "Transmutation",
];

const CHARACTER_CLASSES = [
  "bard",
  "cleric",
  "druid",
  "paladin",
  "ranger",
  "sorcerer",
  "warlock",
  "wizard",
];

export function SpellFilters({ filters, onFilterChange }: SpellFiltersProps) {
  const hasActiveFilters = 
    filters.level !== null ||
    filters.school !== null ||
    filters.characterClass !== null ||
    filters.concentration !== null ||
    filters.ritual !== null;

  const handleClearFilters = () => {
    onFilterChange({
      level: null,
      school: null,
      characterClass: null,
      concentration: null,
      ritual: null,
    });
  };

  return (
    <Card className="h-fit sticky top-4">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Filters</CardTitle>
          {hasActiveFilters && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleClearFilters}
              className="h-8 px-2"
            >
              <X className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Spell Level */}
        <div className="space-y-2">
          <Label>Level</Label>
          <div className="grid grid-cols-2 gap-2">
            {SPELL_LEVELS.map(({ value, label }) => (
              <Button
                key={label}
                type="button"
                variant={filters.level === value ? "default" : "outline"}
                size="sm"
                onClick={() => onFilterChange({ level: value })}
                className="h-8"
              >
                {label}
              </Button>
            ))}
          </div>
        </div>

        {/* School */}
        <div className="space-y-2">
          <Label>School</Label>
          <Select
            value={filters.school || "all"}
            onValueChange={(value) => onFilterChange({ school: value === "all" ? null : value })}
          >
            <SelectTrigger>
              <SelectValue placeholder="All Schools" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Schools</SelectItem>
              {SPELL_SCHOOLS.map((school) => (
                <SelectItem key={school} value={school}>
                  {school}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Class */}
        <div className="space-y-2">
          <Label>Class</Label>
          <Select
            value={filters.characterClass || "all"}
            onValueChange={(value) => onFilterChange({ characterClass: value === "all" ? null : value })}
          >
            <SelectTrigger>
              <SelectValue placeholder="All Classes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Classes</SelectItem>
              {CHARACTER_CLASSES.map((cls) => (
                <SelectItem key={cls} value={cls}>
                  {cls.charAt(0).toUpperCase() + cls.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Concentration */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="concentration"
            checked={filters.concentration === true}
            onCheckedChange={(checked) => 
              onFilterChange({ concentration: checked ? true : null })
            }
          />
          <Label
            htmlFor="concentration"
            className="text-sm font-normal cursor-pointer"
          >
            Concentration only
          </Label>
        </div>

        {/* Ritual */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="ritual"
            checked={filters.ritual === true}
            onCheckedChange={(checked) => 
              onFilterChange({ ritual: checked ? true : null })
            }
          />
          <Label
            htmlFor="ritual"
            className="text-sm font-normal cursor-pointer"
          >
            Ritual only
          </Label>
        </div>
      </CardContent>
    </Card>
  );
}
