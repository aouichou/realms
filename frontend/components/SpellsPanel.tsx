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
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { BookOpen, Clock, Moon, Sparkles, Target, Zap } from "lucide-react";
import { useEffect, useState } from "react";

interface Spell {
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
  available_to_classes: string[];
}

interface CharacterSpell extends Spell {
  is_known: boolean;
  is_prepared: boolean;
}

interface SpellSlots {
  [level: string]: {
    total: number;
    used: number;
  };
}

interface SpellsPanelProps {
  characterId: string;
}

const SPELL_SCHOOLS = [
  "All Schools",
  "Abjuration",
  "Conjuration",
  "Divination",
  "Enchantment",
  "Evocation",
  "Illusion",
  "Necromancy",
  "Transmutation",
];

const SCHOOL_COLORS: Record<string, string> = {
  Abjuration: "bg-blue-500",
  Conjuration: "bg-purple-500",
  Divination: "bg-cyan-500",
  Enchantment: "bg-pink-500",
  Evocation: "bg-red-500",
  Illusion: "bg-indigo-500",
  Necromancy: "bg-gray-700",
  Transmutation: "bg-green-500",
};

export function SpellsPanel({ characterId }: SpellsPanelProps) {
  const [spells, setSpells] = useState<CharacterSpell[]>([]);
  const [spellSlots, setSpellSlots] = useState<SpellSlots>({});
  const [loading, setLoading] = useState(true);
  const [selectedSpell, setSelectedSpell] = useState<CharacterSpell | null>(null);
  const [castDialogOpen, setCastDialogOpen] = useState(false);
  const [prepareDialogOpen, setPrepareDialogOpen] = useState(false);
  const [filterLevel, setFilterLevel] = useState<string>("all");
  const [filterSchool, setFilterSchool] = useState<string>("All Schools");
  const [showPreparedOnly, setShowPreparedOnly] = useState(false);
  const [selectedSpellsToPrepare, setSelectedSpellsToPrepare] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchSpells();
    fetchSpellSlots();
  }, [characterId]);

  const fetchSpells = async () => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/spells/character/${characterId}/spells`
      );
      const data = await response.json();
      setSpells(data);
    } catch (error) {
      console.error("Failed to fetch spells:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSpellSlots = async () => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/spells/character/${characterId}/slots`
      );
      const data = await response.json();
      setSpellSlots(data.spell_slots || {});
    } catch (error) {
      console.error("Failed to fetch spell slots:", error);
    }
  };

  const castSpell = async (spellId: string, spellLevel: number) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/spells/character/${characterId}/cast`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            spell_id: spellId,
            spell_level: spellLevel,
          }),
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        await fetchSpellSlots();
        setCastDialogOpen(false);
        setSelectedSpell(null);
        // Show cast result (you could add a toast notification here)
        console.log("Spell cast result:", data);
      }
    } catch (error) {
      console.error("Failed to cast spell:", error);
    }
  };

  const openPrepareDialog = () => {
    const preparedSpellIds = new Set(
      spells.filter((s) => s.is_prepared).map((s) => s.id)
    );
    setSelectedSpellsToPrepare(preparedSpellIds);
    setPrepareDialogOpen(true);
  };

  const savePreparedSpells = async () => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/spells/character/${characterId}/prepare`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            spell_ids: Array.from(selectedSpellsToPrepare),
          }),
        }
      );
      
      if (response.ok) {
        await fetchSpells();
        setPrepareDialogOpen(false);
      }
    } catch (error) {
      console.error("Failed to prepare spells:", error);
    }
  };

  const longRest = async () => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/spells/character/${characterId}/rest`,
        {
          method: "POST",
        }
      );
      
      if (response.ok) {
        await fetchSpellSlots();
      }
    } catch (error) {
      console.error("Failed to complete long rest:", error);
    }
  };

  const toggleSpellToPrepare = (spellId: string) => {
    const newSet = new Set(selectedSpellsToPrepare);
    if (newSet.has(spellId)) {
      newSet.delete(spellId);
    } else {
      newSet.add(spellId);
    }
    setSelectedSpellsToPrepare(newSet);
  };

  const filteredSpells = spells.filter((spell) => {
    if (filterLevel !== "all" && spell.level !== parseInt(filterLevel)) {
      return false;
    }
    if (filterSchool !== "All Schools" && spell.school !== filterSchool) {
      return false;
    }
    if (showPreparedOnly && !spell.is_prepared) {
      return false;
    }
    return true;
  });

  const groupedSpells = filteredSpells.reduce((acc, spell) => {
    const level = spell.level === 0 ? "Cantrips" : `Level ${spell.level}`;
    if (!acc[level]) acc[level] = [];
    acc[level].push(spell);
    return acc;
  }, {} as Record<string, CharacterSpell[]>);

  const getComponents = (spell: CharacterSpell) => {
    const components = [];
    if (spell.verbal) components.push("V");
    if (spell.somatic) components.push("S");
    if (spell.material) components.push("M");
    return components.join(", ");
  };

  const canCastSpell = (spell: CharacterSpell) => {
    if (spell.level === 0) return true; // Cantrips
    const slots = spellSlots[spell.level.toString()];
    return slots && slots.used < slots.total;
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Actions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              Spells
            </CardTitle>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={openPrepareDialog}
              >
                <BookOpen className="w-4 h-4 mr-2" />
                Prepare Spells
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={longRest}
              >
                <Moon className="w-4 h-4 mr-2" />
                Long Rest
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Spell Slots */}
      {Object.keys(spellSlots).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Spell Slots</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-5 gap-3">
              {Object.entries(spellSlots)
                .sort(([a], [b]) => parseInt(a) - parseInt(b))
                .map(([level, slots]) => (
                  <div key={level} className="text-center">
                    <p className="text-sm text-muted-foreground mb-2">
                      Level {level}
                    </p>
                    <div className="flex gap-1 justify-center flex-wrap mb-1">
                      {Array.from({ length: slots.total }).map((_, i) => (
                        <div
                          key={i}
                          className={`w-3 h-3 rounded-full border-2 ${
                            i < slots.used
                              ? "bg-gray-300 border-gray-400"
                              : "bg-purple-500 border-purple-600"
                          }`}
                        />
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {slots.total - slots.used} / {slots.total}
                    </p>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4 items-center">
            <Select value={filterLevel} onValueChange={setFilterLevel}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="All Levels" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Levels</SelectItem>
                <SelectItem value="0">Cantrips</SelectItem>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((level) => (
                  <SelectItem key={level} value={level.toString()}>
                    Level {level}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filterSchool} onValueChange={setFilterSchool}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Schools" />
              </SelectTrigger>
              <SelectContent>
                {SPELL_SCHOOLS.map((school) => (
                  <SelectItem key={school} value={school}>
                    {school}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              variant={showPreparedOnly ? "default" : "outline"}
              size="sm"
              onClick={() => setShowPreparedOnly(!showPreparedOnly)}
            >
              Prepared Only
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Spells List */}
      <ScrollArea className="h-[500px]">
        <div className="space-y-4">
          {Object.entries(groupedSpells)
            .sort(([a], [b]) => {
              if (a === "Cantrips") return -1;
              if (b === "Cantrips") return 1;
              return parseInt(a.split(" ")[1]) - parseInt(b.split(" ")[1]);
            })
            .map(([level, spellsInLevel]) => (
              <div key={level}>
                <h3 className="font-semibold text-lg mb-3">{level}</h3>
                <div className="grid grid-cols-1 gap-3">
                  {spellsInLevel.map((spell) => (
                    <Card
                      key={spell.id}
                      className={`cursor-pointer transition-all hover:shadow-md ${
                        !spell.is_prepared ? "opacity-60" : ""
                      }`}
                      onClick={() => setSelectedSpell(spell)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-semibold">{spell.name}</h4>
                              <Badge
                                className={`${
                                  SCHOOL_COLORS[spell.school] || "bg-gray-500"
                                } text-white`}
                              >
                                {spell.school}
                              </Badge>
                              {spell.is_prepared && (
                                <Badge variant="outline">Prepared</Badge>
                              )}
                              {spell.is_concentration && (
                                <Badge variant="secondary">Concentration</Badge>
                              )}
                              {spell.is_ritual && (
                                <Badge variant="secondary">Ritual</Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {spell.casting_time}
                              </span>
                              <span className="flex items-center gap-1">
                                <Target className="w-3 h-3" />
                                {spell.range}
                              </span>
                              <span>{getComponents(spell)}</span>
                            </div>
                          </div>
                          {spell.is_prepared && (
                            <Button
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedSpell(spell);
                                setCastDialogOpen(true);
                              }}
                              disabled={!canCastSpell(spell)}
                            >
                              <Zap className="w-4 h-4 mr-1" />
                              Cast
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
        </div>
      </ScrollArea>

      {/* Spell Details Dialog */}
      <Dialog
        open={selectedSpell !== null && !castDialogOpen}
        onOpenChange={(open) => !open && setSelectedSpell(null)}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedSpell?.name}
              <Badge
                className={`${
                  selectedSpell ? SCHOOL_COLORS[selectedSpell.school] : ""
                } text-white`}
              >
                {selectedSpell?.school}
              </Badge>
            </DialogTitle>
            <DialogDescription>
              Level {selectedSpell?.level === 0 ? "Cantrip" : selectedSpell?.level}
            </DialogDescription>
          </DialogHeader>

          {selectedSpell && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium">Casting Time</p>
                  <p className="text-sm text-muted-foreground">
                    {selectedSpell.casting_time}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">Range</p>
                  <p className="text-sm text-muted-foreground">
                    {selectedSpell.range}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">Duration</p>
                  <p className="text-sm text-muted-foreground">
                    {selectedSpell.duration}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">Components</p>
                  <p className="text-sm text-muted-foreground">
                    {getComponents(selectedSpell)}
                    {selectedSpell.material && ` (${selectedSpell.material})`}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-sm font-medium mb-2">Description</p>
                <p className="text-sm text-muted-foreground">
                  {selectedSpell.description}
                </p>
              </div>

              {selectedSpell.damage_dice && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium">Damage</p>
                    <p className="text-sm text-muted-foreground">
                      {selectedSpell.damage_dice} {selectedSpell.damage_type}
                    </p>
                  </div>
                  {selectedSpell.save_ability && (
                    <div>
                      <p className="text-sm font-medium">Saving Throw</p>
                      <p className="text-sm text-muted-foreground">
                        {selectedSpell.save_ability}
                      </p>
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                {selectedSpell.is_concentration && (
                  <Badge variant="secondary">Requires Concentration</Badge>
                )}
                {selectedSpell.is_ritual && (
                  <Badge variant="secondary">Can be cast as Ritual</Badge>
                )}
              </div>
            </div>
          )}

          <DialogFooter>
            {selectedSpell?.is_prepared && (
              <Button
                onClick={() => {
                  setCastDialogOpen(true);
                }}
                disabled={!canCastSpell(selectedSpell)}
              >
                <Zap className="w-4 h-4 mr-2" />
                Cast Spell
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cast Spell Dialog */}
      <Dialog open={castDialogOpen} onOpenChange={setCastDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cast {selectedSpell?.name}</DialogTitle>
            <DialogDescription>
              {selectedSpell?.level === 0
                ? "This is a cantrip and doesn't consume spell slots."
                : `This will consume a level ${selectedSpell?.level} spell slot.`}
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCastDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() =>
                selectedSpell && castSpell(selectedSpell.id, selectedSpell.level)
              }
            >
              <Zap className="w-4 h-4 mr-2" />
              Cast
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Prepare Spells Dialog */}
      <Dialog open={prepareDialogOpen} onOpenChange={setPrepareDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Prepare Spells</DialogTitle>
            <DialogDescription>
              Select which spells you want to prepare for today
            </DialogDescription>
          </DialogHeader>

          <ScrollArea className="h-[400px]">
            <div className="space-y-4">
              {Object.entries(
                spells.reduce((acc, spell) => {
                  if (spell.level === 0) return acc; // Skip cantrips
                  const level = `Level ${spell.level}`;
                  if (!acc[level]) acc[level] = [];
                  acc[level].push(spell);
                  return acc;
                }, {} as Record<string, CharacterSpell[]>)
              ).map(([level, spellsInLevel]) => (
                <div key={level}>
                  <h4 className="font-semibold mb-2">{level}</h4>
                  <div className="space-y-2">
                    {spellsInLevel.map((spell) => (
                      <div
                        key={spell.id}
                        className="flex items-center justify-between p-3 border rounded-lg cursor-pointer hover:bg-accent"
                        onClick={() => toggleSpellToPrepare(spell.id)}
                      >
                        <div className="flex items-center gap-3">
                          <input
                            type="checkbox"
                            checked={selectedSpellsToPrepare.has(spell.id)}
                            onChange={() => toggleSpellToPrepare(spell.id)}
                            className="w-4 h-4"
                          />
                          <div>
                            <p className="font-medium">{spell.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {spell.school} • {spell.casting_time}
                            </p>
                          </div>
                        </div>
                        <Badge
                          className={`${
                            SCHOOL_COLORS[spell.school] || "bg-gray-500"
                          } text-white`}
                        >
                          {spell.school}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPrepareDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={savePreparedSpells}>
              <BookOpen className="w-4 h-4 mr-2" />
              Save Prepared Spells
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
