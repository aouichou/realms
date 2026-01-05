'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
    CLASS_SKILL_PROFICIENCIES,
    RACIAL_SKILL_BONUSES,
    SKILLS,
    type Skill,
    type SkillName,
} from '@/lib/skills';
import { useState } from 'react';

interface SkillProficiencySelectionProps {
  characterClass: string;
  race: string;
  onComplete: (selectedSkills: SkillName[]) => void;
  onBack?: () => void;
}

export default function SkillProficiencySelection({
  characterClass,
  race,
  onComplete,
  onBack,
}: SkillProficiencySelectionProps) {
  const [selectedClassSkills, setSelectedClassSkills] = useState<SkillName[]>([]);
  const [selectedRacialSkills, setSelectedRacialSkills] = useState<SkillName[]>([]);

  const classRules = CLASS_SKILL_PROFICIENCIES[characterClass];
  const racialBonus = RACIAL_SKILL_BONUSES[race] || { skills: [] };

  // Fixed racial skills (e.g., Elf gets Perception)
  const fixedRacialSkills = racialBonus.skills;

  // Racial skills that can be chosen (e.g., Half-Elf chooses 2)
  const racialChoiceCount = racialBonus.chooseCount || 0;
  const racialChoices = racialBonus.chooseFrom || [];

  // Check if selection is complete
  const isClassSelectionComplete = selectedClassSkills.length === classRules.count;
  const isRacialSelectionComplete =
    racialChoiceCount === 0 || selectedRacialSkills.length === racialChoiceCount;
  const isComplete = isClassSelectionComplete && isRacialSelectionComplete;

  const handleClassSkillToggle = (skillName: SkillName) => {
    setSelectedClassSkills((prev) => {
      if (prev.includes(skillName)) {
        return prev.filter((s) => s !== skillName);
      } else if (prev.length < classRules.count) {
        return [...prev, skillName];
      }
      return prev;
    });
  };

  const handleRacialSkillToggle = (skillName: SkillName) => {
    setSelectedRacialSkills((prev) => {
      if (prev.includes(skillName)) {
        return prev.filter((s) => s !== skillName);
      }
      if (prev.length < racialChoiceCount) {
        return [...prev, skillName];
      }
      return prev;
    });
  };

  const handleContinue = () => {
    // Combine all selected skills (class + racial fixed + racial chosen)
    const allSkills = [...new Set([...selectedClassSkills, ...fixedRacialSkills, ...selectedRacialSkills])];
    onComplete(allSkills);
  };

  const getSkillDetails = (skillName: SkillName): Skill => {
    return SKILLS.find((s) => s.name === skillName)!;
  };

  const isSkillDisabled = (skillName: SkillName, isClassSkill: boolean): boolean => {
    if (isClassSkill) {
      return (
        !selectedClassSkills.includes(skillName) &&
        selectedClassSkills.length >= classRules.count
      );
    } else {
      return (
        !selectedRacialSkills.includes(skillName) &&
        selectedRacialSkills.length >= racialChoiceCount
      );
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-bold">Skill Proficiencies</h2>
        <p className="text-muted-foreground">
          Choose your skill proficiencies based on your class and race
        </p>
      </div>

      {/* Class Skills Section */}
      <Card className="p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold flex items-center gap-2">
                {characterClass} Skills
                <Badge variant="default">
                  {selectedClassSkills.length} / {classRules.count} selected
                </Badge>
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                Choose {classRules.count} skill{classRules.count > 1 ? 's' : ''} from the
                following options
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {classRules.choices.map((skillName) => {
              const skill = getSkillDetails(skillName);
              const isSelected = selectedClassSkills.includes(skillName);
              const isDisabled = isSkillDisabled(skillName, true);

              return (
                <div
                  key={skillName}
                  className={`
                    flex items-start gap-3 p-4 rounded-lg border-2 transition-all cursor-pointer
                    ${
                      isSelected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    }
                    ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}
                  `}
                  onClick={() => !isDisabled && handleClassSkillToggle(skillName)}
                >
                  <Checkbox
                    checked={isSelected}
                    disabled={isDisabled}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{skillName}</span>
                      <Badge variant="outline" className="text-xs">
                        {skill.ability.toUpperCase().slice(0, 3)}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {skill.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Racial Skills Section */}
      {(fixedRacialSkills.length > 0 || racialChoiceCount > 0) && (
        <Card className="p-6">
          <div className="space-y-4">
            <div>
              <h3 className="text-xl font-semibold flex items-center gap-2">
                {race} Racial Bonuses
                {racialChoiceCount > 0 && (
                  <Badge variant="default">
                    {selectedRacialSkills.length} / {racialChoiceCount} selected
                  </Badge>
                )}
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                {fixedRacialSkills.length > 0 &&
                  `Automatically gained: ${fixedRacialSkills.join(', ')}`}
                {fixedRacialSkills.length > 0 && racialChoiceCount > 0 && '. '}
                {racialChoiceCount > 0 &&
                  `Choose ${racialChoiceCount} additional skill${racialChoiceCount > 1 ? 's' : ''}`}
              </p>
            </div>

            {/* Fixed Racial Skills */}
            {fixedRacialSkills.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-sm">Granted Skills</h4>
                <div className="flex flex-wrap gap-2">
                  {fixedRacialSkills.map((skillName) => {
                    const skill = getSkillDetails(skillName);
                    return (
                      <Badge
                        key={skillName}
                        variant="secondary"
                        className="text-sm px-3 py-1"
                      >
                        {skillName} ({skill.ability.toUpperCase().slice(0, 3)})
                      </Badge>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Racial Choice Skills */}
            {racialChoiceCount > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {racialChoices.map((skillName) => {
                  const skill = getSkillDetails(skillName);
                  const isSelected = selectedRacialSkills.includes(skillName);
                  const isDisabled = isSkillDisabled(skillName, false);
                  // Disable if already selected as class skill or fixed racial
                  const isAlreadyGranted =
                    selectedClassSkills.includes(skillName) ||
                    fixedRacialSkills.includes(skillName);

                  return (
                    <div
                      key={skillName}
                      className={`
                        flex items-start gap-3 p-4 rounded-lg border-2 transition-all cursor-pointer
                        ${
                          isSelected
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:border-primary/50'
                        }
                        ${
                          isDisabled || isAlreadyGranted
                            ? 'opacity-50 cursor-not-allowed'
                            : ''
                        }
                      `}
                      onClick={() =>
                        !isDisabled && !isAlreadyGranted && handleRacialSkillToggle(skillName)
                      }
                    >
                      <Checkbox
                        checked={isSelected || isAlreadyGranted}
                        disabled={isDisabled || isAlreadyGranted}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{skillName}</span>
                          <Badge variant="outline" className="text-xs">
                            {skill.ability.toUpperCase().slice(0, 3)}
                          </Badge>
                          {isAlreadyGranted && (
                            <Badge variant="secondary" className="text-xs">
                              Already Selected
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {skill.description}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Summary */}
      <Card className="p-4 bg-muted/50">
        <div className="space-y-2">
          <h4 className="font-semibold text-sm">Selected Skill Proficiencies</h4>
          <div className="flex flex-wrap gap-2">
            {[...fixedRacialSkills, ...selectedClassSkills, ...selectedRacialSkills].map(
              (skillName) => {
                const skill = getSkillDetails(skillName);
                return (
                  <Badge key={skillName} variant="default">
                    {skillName} ({skill.ability.toUpperCase().slice(0, 3)})
                  </Badge>
                );
              }
            )}
            {[...fixedRacialSkills, ...selectedClassSkills, ...selectedRacialSkills]
              .length === 0 && (
              <span className="text-sm text-muted-foreground">No skills selected yet</span>
            )}
          </div>
        </div>
      </Card>

      {/* Navigation */}
      <div className="flex justify-between gap-4">
        {onBack && (
          <Button variant="outline" onClick={onBack}>
            Back
          </Button>
        )}
        <Button onClick={handleContinue} disabled={!isComplete} className="ml-auto">
          Continue
        </Button>
      </div>
    </div>
  );
}
