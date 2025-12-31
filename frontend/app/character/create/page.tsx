'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

// D&D 5e Classes and Races from backend API
const DND_CLASSES = [
  { id: 'barbarian', name: 'Barbarian', hitDie: 12 },
  { id: 'bard', name: 'Bard', hitDie: 8 },
  { id: 'cleric', name: 'Cleric', hitDie: 8 },
  { id: 'druid', name: 'Druid', hitDie: 8 },
  { id: 'fighter', name: 'Fighter', hitDie: 10 },
  { id: 'monk', name: 'Monk', hitDie: 8 },
  { id: 'paladin', name: 'Paladin', hitDie: 10 },
  { id: 'ranger', name: 'Ranger', hitDie: 10 },
  { id: 'rogue', name: 'Rogue', hitDie: 8 },
  { id: 'sorcerer', name: 'Sorcerer', hitDie: 6 },
  { id: 'warlock', name: 'Warlock', hitDie: 8 },
  { id: 'wizard', name: 'Wizard', hitDie: 6 },
];

const DND_RACES = [
  'Dragonborn', 'Dwarf', 'Elf', 'Gnome', 'Half-Elf', 'Halfling', 
  'Half-Orc', 'Human', 'Tiefling'
];

interface AbilityScores {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

export default function CharacterCreation() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [selectedClass, setSelectedClass] = useState('');
  const [selectedRace, setSelectedRace] = useState('');
  const [level, setLevel] = useState(1);
  const [abilities, setAbilities] = useState<AbilityScores>({
    strength: 10,
    dexterity: 10,
    constitution: 10,
    intelligence: 10,
    wisdom: 10,
    charisma: 10,
  });

  const calculateModifier = (score: number): number => {
    return Math.floor((score - 10) / 2);
  };

  const calculateHP = (): number => {
    const classData = DND_CLASSES.find(c => c.id === selectedClass);
    if (!classData) return 0;
    
    const conModifier = calculateModifier(abilities.constitution);
    return classData.hitDie + conModifier;
  };

  const handleAbilityChange = (ability: keyof AbilityScores, value: string) => {
    const numValue = parseInt(value) || 10;
    const clampedValue = Math.max(1, Math.min(20, numValue));
    setAbilities(prev => ({ ...prev, [ability]: clampedValue }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const characterData = {
      name,
      character_class: selectedClass,
      race: selectedRace,
      level,
      ability_scores: abilities,
    };

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/characters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(characterData),
      });

      if (response.ok) {
        const character = await response.json();
        console.log('Character created:', character);
        // Navigate to game with the new character
        router.push(`/game/${character.id}`);
      } else {
        console.error('Failed to create character');
      }
    } catch (error) {
      console.error('Error creating character:', error);
    }
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="font-display text-5xl text-primary-900 mb-2 text-center">
          Create Your Hero
        </h1>
        <p className="text-center text-muted-foreground mb-8 font-body">
          Forge your legend in the Mistral Realms
        </p>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-6 md:grid-cols-2">
            {/* Basic Info */}
            <Card>
              <CardHeader>
                <CardTitle className="font-display">Character Details</CardTitle>
                <CardDescription>The essentials of your hero</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Character Name</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your character's name"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="race">Race</Label>
                  <Select value={selectedRace} onValueChange={setSelectedRace} required>
                    <SelectTrigger id="race">
                      <SelectValue placeholder="Select a race" />
                    </SelectTrigger>
                    <SelectContent>
                      {DND_RACES.map((race) => (
                        <SelectItem key={race} value={race.toLowerCase()}>
                          {race}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="class">Class</Label>
                  <Select value={selectedClass} onValueChange={setSelectedClass} required>
                    <SelectTrigger id="class">
                      <SelectValue placeholder="Select a class" />
                    </SelectTrigger>
                    <SelectContent>
                      {DND_CLASSES.map((cls) => (
                        <SelectItem key={cls.id} value={cls.id}>
                          {cls.name} (d{cls.hitDie})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="level">Level</Label>
                  <Input
                    id="level"
                    type="number"
                    value={level}
                    onChange={(e) => setLevel(parseInt(e.target.value) || 1)}
                    min="1"
                    max="20"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Ability Scores */}
            <Card>
              <CardHeader>
                <CardTitle className="font-display">Ability Scores</CardTitle>
                <CardDescription>Your hero's core attributes</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(abilities).map(([ability, score]) => (
                    <div key={ability} className="space-y-2">
                      <Label htmlFor={ability} className="capitalize">
                        {ability}
                      </Label>
                      <div className="flex gap-2 items-center">
                        <Input
                          id={ability}
                          type="number"
                          value={score}
                          onChange={(e) => handleAbilityChange(ability as keyof AbilityScores, e.target.value)}
                          min="1"
                          max="20"
                          className="w-16"
                        />
                        <span className="text-sm text-muted-foreground font-mono w-12">
                          {calculateModifier(score) >= 0 ? '+' : ''}{calculateModifier(score)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Character Preview */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="font-display">Character Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-lg font-body">
                    <span className="font-semibold">{name || 'Unnamed Hero'}</span>
                    {selectedRace && selectedClass && (
                      <span className="text-muted-foreground">
                        {' '}- Level {level} {selectedRace.charAt(0).toUpperCase() + selectedRace.slice(1)} {DND_CLASSES.find(c => c.id === selectedClass)?.name}
                      </span>
                    )}
                  </p>
                  {selectedClass && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Hit Points: <span className="font-bold text-success-500">{calculateHP()}</span>
                    </p>
                  )}
                </div>
                <Button 
                  type="submit" 
                  size="lg"
                  disabled={!name || !selectedClass || !selectedRace}
                  className="font-body"
                >
                  Create Character
                </Button>
              </div>
            </CardContent>
          </Card>
        </form>
      </div>
    </div>
  );
}
