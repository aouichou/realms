import React, { useState, useEffect } from 'react';
import { Dices, TrendingUp, TrendingDown, Target, Swords, Shield } from 'lucide-react';

interface DiceRoll {
  type: string;
  description: string;
  notation: string;
  rolls: number[];
  modifier: number;
  total: number;
  dc?: number;
  success?: boolean;
  advantage?: boolean;
  disadvantage?: boolean;
  is_critical?: boolean;
  is_critical_fail?: boolean;
}

interface DiceRollResultProps {
  rolls: DiceRoll[];
  onClose?: () => void;
}

export default function DiceRollResult({ rolls, onClose }: DiceRollResultProps) {
  const [animatingIndex, setAnimatingIndex] = useState(-1);

  // Animate rolls one by one
  useEffect(() => {
    if (rolls.length > 0) {
      rolls.forEach((_, index) => {
        setTimeout(() => {
          setAnimatingIndex(index);
        }, index * 300);
      });
    }
  }, [rolls]);

  if (!rolls || rolls.length === 0) {
    return null;
  }

  const getRollIcon = (type: string) => {
    switch (type) {
      case 'attack':
        return <Swords className="w-4 h-4" />;
      case 'save':
        return <Shield className="w-4 h-4" />;
      case 'check':
        return <Target className="w-4 h-4" />;
      default:
        return <Dices className="w-4 h-4" />;
    }
  };

  const getRollColor = (roll: DiceRoll) => {
    if (roll.is_critical) return 'border-yellow-500 bg-yellow-50';
    if (roll.is_critical_fail) return 'border-red-500 bg-red-50';
    if (roll.success === true) return 'border-green-500 bg-green-50';
    if (roll.success === false) return 'border-red-500 bg-red-50';
    return 'border-blue-500 bg-blue-50';
  };

  const getRollBadge = (roll: DiceRoll) => {
    if (roll.is_critical) return { text: "CRITICAL!", color: "bg-yellow-500 text-white" };
    if (roll.is_critical_fail) return { text: "CRITICAL FAIL!", color: "bg-red-500 text-white" };
    if (roll.success === true) return { text: "SUCCESS", color: "bg-green-500 text-white" };
    if (roll.success === false) return { text: "FAILURE", color: "bg-red-500 text-white" };
    return null;
  };

  return (
    <div className="space-y-3 my-4">
      {rolls.map((roll, index) => {
        const badge = getRollBadge(roll);
        const isAnimating = animatingIndex === index;

        return (
          <div
            key={index}
            className={`
              border-2 rounded-lg p-4 transition-all duration-500
              ${getRollColor(roll)}
              ${isAnimating ? 'scale-105 animate-pulse' : 'scale-100'}
            `}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-white rounded">{getRollIcon(roll.type)}</div>
                <div>
                  <div className="font-bold text-sm text-gray-900">{roll.description}</div>
                  <div className="text-xs text-gray-600">{roll.notation}</div>
                </div>
              </div>
              {badge && (
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${badge.color}`}>
                  {badge.text}
                </span>
              )}
            </div>

            {/* Dice Breakdown */}
            <div className="flex items-center gap-2 flex-wrap mb-2">
              {roll.rolls.map((die, diceIndex) => (
                <div
                  key={diceIndex}
                  className={`
                    w-10 h-10 flex items-center justify-center
                    bg-white border-2 rounded-md font-bold
                    transition-all duration-300
                    ${die === 20 ? 'border-yellow-400 text-yellow-600' : ''}
                    ${die === 1 ? 'border-red-400 text-red-600' : ''}
                    ${die !== 1 && die !== 20 ? 'border-gray-300 text-gray-700' : ''}
                    ${isAnimating ? 'animate-spin' : ''}
                  `}
                  style={{ animationDelay: `${diceIndex * 100}ms` }}
                >
                  {die}
                </div>
              ))}

              {/* Modifier */}
              {roll.modifier !== 0 && (
                <div className="flex items-center gap-1 text-sm text-gray-700">
                  {roll.modifier > 0 ? (
                    <TrendingUp className="w-4 h-4 text-green-600" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-600" />
                  )}
                  <span className="font-semibold">
                    {roll.modifier > 0 ? '+' : ''}
                    {roll.modifier}
                  </span>
                </div>
              )}
            </div>

            {/* Total and DC */}
            <div className="flex items-center justify-between border-t pt-2">
              <div className="text-2xl font-bold text-gray-900">
                Total: <span className="text-blue-600">{roll.total}</span>
              </div>
              {roll.dc !== undefined && (
                <div className="text-sm font-medium text-gray-600">DC {roll.dc}</div>
              )}
            </div>

            {/* Advantage/Disadvantage Indicator */}
            {(roll.advantage || roll.disadvantage) && (
              <div className="mt-2 text-xs text-gray-600 italic">
                {roll.advantage && 'Rolled with advantage (took higher)'}
                {roll.disadvantage && 'Rolled with disadvantage (took lower)'}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
