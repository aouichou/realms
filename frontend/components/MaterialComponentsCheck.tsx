"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertCircle, Check, PackageOpen } from "lucide-react";

interface MaterialComponent {
  description: string;
  cost?: number; // in gold pieces
  consumed?: boolean;
}

interface MaterialComponentsCheckProps {
  spell: {
    name: string;
    components: {
      material?: MaterialComponent;
    };
  };
  characterInventory?: {
    gold: number;
    items: Array<{ name: string; quantity: number }>;
  };
  onConfirm?: () => void;
  onCancel?: () => void;
}

export function MaterialComponentsCheck({
  spell,
  characterInventory,
  onConfirm,
  onCancel,
}: MaterialComponentsCheckProps) {
  const material = spell.components.material;

  if (!material) {
    // No material components needed
    return null;
  }

  const isExpensive = (material.cost ?? 0) >= 50;
  const hasEnoughGold = (characterInventory?.gold ?? 0) >= (material.cost ?? 0);
  
  // Check if character has the specific component
  const hasComponent = characterInventory?.items.some(
    item => item.name.toLowerCase().includes(material.description.toLowerCase())
  ) ?? false;

  const canCast = !isExpensive || (hasEnoughGold && (material.consumed ? hasComponent : true));

  return (
    <div className="space-y-3">
      <Alert variant={canCast ? "default" : "destructive"}>
        <PackageOpen className="h-4 w-4" />
        <AlertTitle>Material Components Required</AlertTitle>
        <AlertDescription>
          <div className="mt-2 space-y-2">
            <p className="text-sm">{material.description}</p>
            
            {material.cost && (
              <div className="flex items-center gap-2">
                <Badge variant={hasEnoughGold ? "default" : "destructive"}>
                  Cost: {material.cost} gp
                </Badge>
                {material.consumed && (
                  <Badge variant="outline">Consumed on cast</Badge>
                )}
              </div>
            )}

            {isExpensive && (
              <div className="space-y-2">
                <p className="text-xs font-semibold">
                  {hasEnoughGold ? (
                    <span className="text-green-600 flex items-center gap-1">
                      <Check className="h-3 w-3" /> You have enough gold
                    </span>
                  ) : (
                    <span className="text-red-600 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" /> Insufficient gold (have {characterInventory?.gold ?? 0} gp)
                    </span>
                  )}
                </p>
                
                {material.consumed && (
                  <p className="text-xs font-semibold">
                    {hasComponent ? (
                      <span className="text-green-600 flex items-center gap-1">
                        <Check className="h-3 w-3" /> Component in inventory
                      </span>
                    ) : (
                      <span className="text-red-600 flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" /> Component not found in inventory
                      </span>
                    )}
                  </p>
                )}
              </div>
            )}

            {!isExpensive && (
              <p className="text-xs text-muted-foreground">
                Can be provided by a component pouch or spellcasting focus
              </p>
            )}
          </div>
        </AlertDescription>
      </Alert>

      {onConfirm && onCancel && (
        <div className="flex gap-2">
          <Button
            onClick={onConfirm}
            disabled={!canCast}
            size="sm"
            className="flex-1"
          >
            {material.consumed ? "Use Component & Cast" : "Cast Spell"}
          </Button>
          <Button
            onClick={onCancel}
            variant="outline"
            size="sm"
          >
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}

// Helper to check if spell can be cast based on materials
export function canCastWithMaterials(
  spell: {
    components: {
      material?: MaterialComponent;
    };
  },
  inventory?: {
    gold: number;
    items: Array<{ name: string; quantity: number }>;
  }
): { canCast: boolean; reason?: string } {
  const material = spell.components.material;

  if (!material) {
    return { canCast: true };
  }

  const isExpensive = (material.cost ?? 0) >= 50;

  if (!isExpensive) {
    // Assume component pouch or focus
    return { canCast: true };
  }

  const hasEnoughGold = (inventory?.gold ?? 0) >= (material.cost ?? 0);
  
  if (!hasEnoughGold) {
    return {
      canCast: false,
      reason: `Insufficient gold. Need ${material.cost} gp, have ${inventory?.gold ?? 0} gp`,
    };
  }

  if (material.consumed) {
    const hasComponent = inventory?.items.some(
      item => item.name.toLowerCase().includes(material.description.toLowerCase())
    ) ?? false;

    if (!hasComponent) {
      return {
        canCast: false,
        reason: `Missing material component: ${material.description}`,
      };
    }
  }

  return { canCast: true };
}
