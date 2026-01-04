"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { BookOpen, Check, Info } from "lucide-react";
import { useEffect, useState } from "react";

interface Spell {
  id: string;
  name: string;
  level: number;
  school: string;
  description: string;
  is_concentration: boolean;
  is_ritual: boolean;
}

interface CharacterSpell {
  id: string;
  spell_id: string;
  is_known: boolean;
  is_prepared: boolean;
  spell: Spell;
}

interface SpellPreparationPanelProps {
  characterId: string;
  characterClass: string;
  level: number;
  spellcastingAbility: string;
  abilityModifier: number;
}

// Classes that prepare spells daily
const PREPARED_CASTERS = ['cleric', 'druid', 'paladin', 'wizard'];

export function SpellPreparationPanel({
  characterId,
  characterClass,
  level,
  spellcastingAbility,
  abilityModifier,
}: SpellPreparationPanelProps) {
  const [knownSpells, setKnownSpells] = useState<CharacterSpell[]>([]);
  const [preparedSpells, setPreparedSpells] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { showToast } = useToast();

  const isPreparedCaster = PREPARED_CASTERS.includes(characterClass.toLowerCase());

  useEffect(() => {
    fetchSpells();
  }, [characterId]);

  const fetchSpells = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/spells/character/${characterId}/spells`
      );
      
      if (response.ok) {
        const data: CharacterSpell[] = await response.json();
        setKnownSpells(data);
        
        // Set currently prepared spells
        const prepared = new Set(
          data.filter(cs => cs.is_prepared).map(cs => cs.spell_id)
        );
        setPreparedSpells(prepared);
      }
    } catch (error) {
      console.error("Failed to fetch spells:", error);
    } finally {
      setLoading(false);
    }
  };

  const calculateMaxPrepared = (): number => {
    if (characterClass.toLowerCase() === 'paladin') {
      return Math.max(1, abilityModifier + Math.floor(level / 2));
    }
    return Math.max(1, abilityModifier + level);
  };

  const toggleSpellPreparation = (spellId: string) => {
    const newPrepared = new Set(preparedSpells);
    
    if (newPrepared.has(spellId)) {
      newPrepared.delete(spellId);
    } else {
      // Check if we can prepare more spells
      if (newPrepared.size >= calculateMaxPrepared()) {
        showToast(`Maximum of ${calculateMaxPrepared()} spells can be prepared`, 'error');
        return;
      }
      newPrepared.add(spellId);
    }
    
    setPreparedSpells(newPrepared);
  };

  const handleSavePreparation = async () => {
    setSaving(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/spells/character/${characterId}/prepare`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            spell_ids: Array.from(preparedSpells),
          }),
        }
      );

      if (response.ok) {
        showToast('Spells prepared successfully!', 'success');
        fetchSpells();
      } else {
        showToast('Failed to prepare spells', 'error');
      }
    } catch (error) {
      console.error("Failed to prepare spells:", error);
      showToast('Failed to prepare spells', 'error');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = () => {
    const currentPrepared = new Set(
      knownSpells.filter(cs => cs.is_prepared).map(cs => cs.spell_id)
    );
    
    if (currentPrepared.size !== preparedSpells.size) return true;
    
    for (const id of preparedSpells) {
      if (!currentPrepared.has(id)) return true;
    }
    
    return false;
  };

  if (!isPreparedCaster) {
    return (
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          {characterClass}s know their spells and don't need to prepare them daily.
        </AlertDescription>
      </Alert>
    );
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Spell Preparation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading spells...</p>
        </CardContent>
      </Card>
    );
  }

  const maxPrepared = calculateMaxPrepared();
  const cantrips = knownSpells.filter(cs => cs.spell.level === 0);
  const leveledSpells = knownSpells.filter(cs => cs.spell.level > 0);

  // Group spells by level
  const spellsByLevel = leveledSpells.reduce((acc, cs) => {
    const level = cs.spell.level;
    if (!acc[level]) acc[level] = [];
    acc[level].push(cs);
    return acc;
  }, {} as Record<number, CharacterSpell[]>);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Spell Preparation</CardTitle>
        <CardDescription>
          You can prepare {maxPrepared} spells from your spellbook.
          Currently prepared: {preparedSpells.size} / {maxPrepared}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Info Alert */}
        <Alert>
          <BookOpen className="h-4 w-4" />
          <AlertDescription>
            As a {characterClass}, you can change your prepared spells after a long rest.
            Your spellcasting ability is <strong>{spellcastingAbility.charAt(0).toUpperCase() + spellcastingAbility.slice(1)}</strong> (modifier: {abilityModifier >= 0 ? '+' : ''}{abilityModifier}).
          </AlertDescription>
        </Alert>

        {/* Spell Lists */}
        <Tabs defaultValue="prepare">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="prepare">Prepare Spells</TabsTrigger>
            <TabsTrigger value="current">Currently Prepared</TabsTrigger>
          </TabsList>

          <TabsContent value="prepare" className="space-y-4">
            <ScrollArea className="h-[500px]">
              <div className="space-y-4">
                {/* Cantrips (always available) */}
                {cantrips.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                      Cantrips
                      <Badge variant="secondary" className="text-xs">
                        Always Available
                      </Badge>
                    </h3>
                    <div className="space-y-2">
                      {cantrips.map((cs) => (
                        <div
                          key={cs.id}
                          className="flex items-start gap-2 p-2 rounded border"
                        >
                          <Check className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                          <div className="flex-1">
                            <div className="font-medium text-sm">{cs.spell.name}</div>
                            <p className="text-xs text-muted-foreground line-clamp-1">
                              {cs.spell.description}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Leveled Spells */}
                {Object.entries(spellsByLevel)
                  .sort(([a], [b]) => parseInt(a) - parseInt(b))
                  .map(([level, spellList]) => (
                    <div key={level}>
                      <h3 className="text-sm font-semibold mb-2">Level {level}</h3>
                      <div className="space-y-2">
                        {spellList.map((cs) => (
                          <div
                            key={cs.id}
                            className="flex items-start gap-2 p-2 rounded border hover:bg-accent transition-colors cursor-pointer"
                            onClick={() => toggleSpellPreparation(cs.spell_id)}
                          >
                            <Checkbox
                              checked={preparedSpells.has(cs.spell_id)}
                              onCheckedChange={() => toggleSpellPreparation(cs.spell_id)}
                              className="mt-0.5"
                            />
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-sm">{cs.spell.name}</span>
                                {cs.spell.is_concentration && (
                                  <Badge variant="outline" className="text-xs">Concentration</Badge>
                                )}
                                {cs.spell.is_ritual && (
                                  <Badge variant="outline" className="text-xs">Ritual</Badge>
                                )}
                              </div>
                              <p className="text-xs text-muted-foreground line-clamp-1 mt-1">
                                {cs.spell.description}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}

                {leveledSpells.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No spells in your spellbook yet. Learn spells from scrolls or by leveling up.
                  </p>
                )}
              </div>
            </ScrollArea>

            {/* Save Button */}
            {hasChanges() && (
              <Button
                onClick={handleSavePreparation}
                disabled={saving || preparedSpells.size > maxPrepared}
                className="w-full"
              >
                {saving ? 'Saving...' : `Save Preparation (${preparedSpells.size}/${maxPrepared})`}
              </Button>
            )}
          </TabsContent>

          <TabsContent value="current">
            <ScrollArea className="h-[500px]">
              <div className="space-y-2">
                {Array.from(preparedSpells).map(spellId => {
                  const cs = knownSpells.find(k => k.spell_id === spellId);
                  if (!cs) return null;
                  
                  return (
                    <div
                      key={cs.id}
                      className="flex items-start gap-2 p-3 rounded border"
                    >
                      <Check className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{cs.spell.name}</span>
                          <Badge variant="outline">
                            Level {cs.spell.level}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {cs.spell.description}
                        </p>
                      </div>
                    </div>
                  );
                })}
                
                {preparedSpells.size === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No spells currently prepared. Switch to the "Prepare Spells" tab to select your spells for the day.
                  </p>
                )}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
