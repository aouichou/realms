// SaveGameButton.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Save } from 'lucide-react';
import { SaveGameModal } from './SaveGameModal';

interface SaveGameButtonProps {
  sessionId: string;
  characterName: string;
}

export function SaveGameButton({ sessionId, characterName }: SaveGameButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsModalOpen(true)}
        className="gap-2"
      >
        <Save className="w-4 h-4" />
        Save Game
      </Button>
      
      <SaveGameModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        sessionId={sessionId}
        characterName={characterName}
      />
    </>
  );
}
