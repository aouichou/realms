"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
    Brain,
    CheckCircle2,
    Dices,
    Eye,
    Footprints,
    MessageCircle,
    Search,
    TrendingDown,
    TrendingUp,
    Users,
    XCircle
} from "lucide-react";
import { useEffect, useState } from "react";

interface AbilityCheckPanelProps {
  characterId: string;
}

interface Skill {
  name: string;
  ability: string;
  isProficient: boolean;
  modifier: number;
}

interface RollResult {
  skill: string;
  roll: number;
  total: number;
  modifier: number;
  proficiency_bonus: number;
  advantage: boolean;
  disadvantage: boolean;
  dc?: number;
  success?: boolean;
  rolls?: number[];
  timestamp: string;
}

const SKILLS_BY_ABILITY: Record<string, string[]> = {
  STR: ["Athletics"],
  DEX: ["Acrobatics", "Sleight of Hand", "Stealth"],
  CON: [],
  INT: ["Arcana", "History", "Investigation", "Nature", "Religion"],
  WIS: ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
  CHA: ["Deception", "Intimidation", "Performance", "Persuasion"],
};

// Map display names to API snake_case format
const SKILL_NAME_MAP: Record<string, string> = {
  "Athletics": "athletics",
  "Acrobatics": "acrobatics",
  "Sleight of Hand": "sleight_of_hand",
  "Stealth": "stealth",
  "Arcana": "arcana",
  "History": "history",
  "Investigation": "investigation",
  "Nature": "nature",
  "Religion": "religion",
  "Animal Handling": "animal_handling",
  "Insight": "insight",
  "Medicine": "medicine",
  "Perception": "perception",
  "Survival": "survival",
  "Deception": "deception",
  "Intimidation": "intimidation",
  "Performance": "performance",
  "Persuasion": "persuasion",
};

// Map skills to their primary ability
const SKILL_TO_ABILITY: Record<string, string> = {
  "Athletics": "strength",
  "Acrobatics": "dexterity",
  "Sleight of Hand": "dexterity",
  "Stealth": "dexterity",
  "Arcana": "intelligence",
  "History": "intelligence",
  "Investigation": "intelligence",
  "Nature": "intelligence",
  "Religion": "intelligence",
  "Animal Handling": "wisdom",
  "Insight": "wisdom",
  "Medicine": "wisdom",
  "Perception": "wisdom",
  "Survival": "wisdom",
  "Deception": "charisma",
  "Intimidation": "charisma",
  "Performance": "charisma",
  "Persuasion": "charisma",
};

const ABILITY_ICONS: Record<string, any> = {
  STR: "💪",
  DEX: "🏃",
  INT: "🧠",
  WIS: "👁️",
  CHA: "💬",
};

const QUICK_CHECKS = [
  { name: "Perception", icon: Eye },
  { name: "Stealth", icon: Footprints },
  { name: "Investigation", icon: Search },
  { name: "Insight", icon: Brain },
  { name: "Persuasion", icon: MessageCircle },
  { name: "Deception", icon: Users },
];

export function AbilityCheckPanel({ characterId }: AbilityCheckPanelProps) {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSkill, setSelectedSkill] = useState<string>("");
  const [advantage, setAdvantage] = useState(false);
  const [disadvantage, setDisadvantage] = useState(false);
  const [dc, setDc] = useState<number | "">("");
  const [rolling, setRolling] = useState(false);
  const [rollHistory, setRollHistory] = useState<RollResult[]>([]);

  useEffect(() => {
    fetchSkills();
  }, [characterId]);

  const fetchSkills = async () => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/characters/${characterId}/stats`
      );
      const data = await response.json();
      
      // Build skills array from the data
      const skillsList: Skill[] = [];
      
      Object.entries(SKILLS_BY_ABILITY).forEach(([ability, abilitySkills]) => {
        abilitySkills.forEach((skillName) => {
          const skillData = data.skills[skillName];
          skillsList.push({
            name: skillName,
            ability,
            isProficient: skillData.proficient,
            modifier: skillData.modifier,
          });
        });
      });
      
      setSkills(skillsList);
    } catch (error) {
      console.error("Failed to fetch skills:", error);
    } finally {
      setLoading(false);
    }
  };

  const performCheck = async (skillName: string) => {
    setRolling(true);
    try {
      // Convert skill name to API format
      const apiSkillName = SKILL_NAME_MAP[skillName];
      const ability = SKILL_TO_ABILITY[skillName];
      
      const response = await fetch(
        `http://localhost:8000/api/dice/check`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            character_id: characterId, // Send as UUID string
            ability: ability,
            skill: apiSkillName,
            advantage,
            disadvantage,
            dc: dc || undefined,
          }),
        }
      );
      
      const data = await response.json();
      
      const result: RollResult = {
        skill: skillName,
        roll: data.roll,
        total: data.total,
        modifier: data.modifier,
        proficiency_bonus: data.proficiency_bonus,
        advantage: data.advantage || false,
        disadvantage: data.disadvantage || false,
        dc: data.dc,
        success: data.success,
        rolls: data.rolls,
        timestamp: new Date().toLocaleTimeString(),
      };
      
      setRollHistory([result, ...rollHistory.slice(0, 4)]);
      
      // Reset toggles after roll
      setAdvantage(false);
      setDisadvantage(false);
    } catch (error) {
      console.error("Failed to perform check:", error);
    } finally {
      setRolling(false);
    }
  };

  const quickCheck = (skillName: string) => {
    setSelectedSkill(skillName);
    performCheck(skillName);
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
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Dices className="w-5 h-5" />
            Ability Checks & Skills
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Quick Checks */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Quick Checks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-2">
            {QUICK_CHECKS.map((check) => {
              const Icon = check.icon;
              return (
                <Button
                  key={check.name}
                  variant="outline"
                  onClick={() => quickCheck(check.name)}
                  disabled={rolling}
                  className="flex items-center gap-2"
                >
                  <Icon className="w-4 h-4" />
                  {check.name}
                </Button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Roll Modifiers */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Roll Modifiers</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex gap-2">
              <Button
                variant={advantage ? "default" : "outline"}
                onClick={() => {
                  setAdvantage(!advantage);
                  if (!advantage) setDisadvantage(false);
                }}
                className="flex-1"
                disabled={disadvantage}
              >
                <TrendingUp className="w-4 h-4 mr-2" />
                Advantage
              </Button>
              <Button
                variant={disadvantage ? "default" : "outline"}
                onClick={() => {
                  setDisadvantage(!disadvantage);
                  if (!disadvantage) setAdvantage(false);
                }}
                className="flex-1"
                disabled={advantage}
              >
                <TrendingDown className="w-4 h-4 mr-2" />
                Disadvantage
              </Button>
            </div>
            
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium min-w-[80px]">
                Target DC:
              </label>
              <Input
                type="number"
                value={dc}
                onChange={(e) => setDc(e.target.value ? parseInt(e.target.value) : "")}
                placeholder="Optional"
                className="flex-1"
                min="1"
                max="30"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Skills by Ability */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">All Skills</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[300px]">
            <div className="space-y-4">
              {Object.entries(SKILLS_BY_ABILITY).map(([ability, abilitySkills]) => {
                if (abilitySkills.length === 0) return null;
                
                return (
                  <div key={ability}>
                    <h4 className="font-semibold mb-2 flex items-center gap-2">
                      <span className="text-2xl">{ABILITY_ICONS[ability]}</span>
                      {ability}
                    </h4>
                    <div className="space-y-2">
                      {abilitySkills.map((skillName) => {
                        const skill = skills.find((s) => s.name === skillName);
                        if (!skill) return null;
                        
                        return (
                          <div
                            key={skillName}
                            className={`flex items-center justify-between p-3 border rounded-lg cursor-pointer hover:bg-accent transition-colors ${
                              selectedSkill === skillName ? "bg-accent" : ""
                            }`}
                            onClick={() => setSelectedSkill(skillName)}
                          >
                            <div className="flex items-center gap-3">
                              <div
                                className={`w-3 h-3 rounded-full ${
                                  skill.isProficient ? "bg-green-500" : "bg-gray-300"
                                }`}
                                title={skill.isProficient ? "Proficient" : "Not proficient"}
                              />
                              <span className="font-medium">{skillName}</span>
                              <Badge variant="secondary">
                                {skill.modifier >= 0 ? "+" : ""}
                                {skill.modifier}
                              </Badge>
                            </div>
                            <Button
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                performCheck(skillName);
                              }}
                              disabled={rolling}
                            >
                              <Dices className="w-4 h-4 mr-1" />
                              Roll
                            </Button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Roll History */}
      {rollHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Rolls</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {rollHistory.map((result, index) => (
                <Card
                  key={index}
                  className={`${
                    result.success === true
                      ? "bg-green-500/10 border-green-500/30"
                      : result.success === false
                      ? "bg-red-500/10 border-red-500/30"
                      : ""
                  }`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold">{result.skill}</span>
                          {result.advantage && (
                            <Badge variant="secondary" className="text-xs">
                              <TrendingUp className="w-3 h-3 mr-1" />
                              Adv
                            </Badge>
                          )}
                          {result.disadvantage && (
                            <Badge variant="secondary" className="text-xs">
                              <TrendingDown className="w-3 h-3 mr-1" />
                              Dis
                            </Badge>
                          )}
                          {result.dc && (
                            <Badge variant="outline" className="text-xs">
                              DC {result.dc}
                            </Badge>
                          )}
                          <span className="text-xs text-muted-foreground">
                            {result.timestamp}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          {result.rolls && result.rolls.length > 1 ? (
                            <span className="font-mono">
                              Rolls: [{result.rolls.join(", ")}] + {result.modifier ?? 0} = {result.total}
                            </span>
                          ) : (
                            <span className="font-mono">
                              d20: {result.roll} + {result.modifier ?? 0} = {result.total}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="text-3xl font-bold">{result.total}</div>
                        {result.success !== undefined && (
                          result.success ? (
                            <CheckCircle2 className="w-6 h-6 text-green-500" />
                          ) : (
                            <XCircle className="w-6 h-6 text-red-500" />
                          )
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}