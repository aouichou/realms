'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import Image from 'next/image';
import { useParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  scene_image_url?: string;
}

interface Character {
  id: number;
  name: string;
  character_class: string;
  race: string;
  level: number;
  hp_current: number;
  hp_max: number;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

type PanelType = 'stats' | 'inventory' | 'dice' | null;

export default function GamePage() {
  const params = useParams();
  const characterId = params.characterId as string;
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [character, setCharacter] = useState<Character | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [openPanel, setOpenPanel] = useState<PanelType>(null);
  const [diceNotation, setDiceNotation] = useState('1d20');
  const [lastDiceResult, setLastDiceResult] = useState<any>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    loadCharacter();
  }, [characterId]);

  useEffect(() => {
    if (character && !sessionId) {
      getOrCreateSession();
    }
  }, [character]);

  useEffect(() => {
    if (sessionId) {
      loadConversationHistory();
    }
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadCharacter = async () => {
    try {
      const response = await fetch(`${API_URL}/api/characters/${characterId}`);
      if (response.ok) {
        const data = await response.json();
        setCharacter(data);
      }
    } catch (error) {
      console.error('Error loading character:', error);
    }
  };

  const getOrCreateSession = async () => {
    try {
      // For now, create a new session every time
      // TODO: Implement logic to get active session or create new one
      const response = await fetch(`${API_URL}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          character_id: characterId,
          companion_id: null,
          current_location: 'Starting Village',
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setSessionId(data.id);
      } else {
        console.error('Error creating session:', await response.text());
      }
    } catch (error) {
      console.error('Error getting/creating session:', error);
    }
  };

  const loadConversationHistory = async () => {
    if (!sessionId) return;
    
    try {
      const response = await fetch(`${API_URL}/api/conversations/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
      }
    } catch (error) {
      console.error('Error loading conversation history:', error);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    // Add user message immediately
    const tempUserMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const response = await fetch(`${API_URL}/api/conversations/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          character_id: parseInt(characterId),
          message: userMessage,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const dmMessage: Message = {
          id: Date.now() + 1,
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString(),
          scene_image_url: data.scene_image_url,
        };
        setMessages(prev => [...prev, dmMessage]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const rollDice = async () => {
    try {
      const response = await fetch(`${API_URL}/api/dice/roll`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dice: diceNotation }),
      });

      if (response.ok) {
        const result = await response.json();
        setLastDiceResult(result);
      }
    } catch (error) {
      console.error('Error rolling dice:', error);
    }
  };

  const calculateModifier = (score: number): number => {
    return Math.floor((score - 10) / 2);
  };

  const togglePanel = (panel: PanelType) => {
    setOpenPanel(openPanel === panel ? null : panel);
  };

  const latestSceneImage = [...messages].reverse().find(m => m.scene_image_url)?.scene_image_url;

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-neutral-900">
      {/* Scene Background Image */}
      {latestSceneImage && (
        <div className="absolute inset-0 z-0">
          <Image
            src={latestSceneImage}
            alt="Current scene"
            fill
            className="object-cover opacity-60"
            priority
          />
        </div>
      )}

      {/* Main Layout */}
      <div className="relative z-10 h-full flex">
        {/* Left Sidebar - Collapsible Panels */}
        <div className="w-64 p-4 space-y-3">
          {/* Stats Button */}
          <button
            onClick={() => togglePanel('stats')}
            className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20 
                     hover:bg-white/20 transition-all text-white font-body text-sm"
          >
            ⚔️ Character Stats
          </button>

          {/* Inventory Button */}
          <button
            onClick={() => togglePanel('inventory')}
            className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20 
                     hover:bg-white/20 transition-all text-white font-body text-sm"
          >
            🎒 Inventory
          </button>

          {/* Dice Button */}
          <button
            onClick={() => togglePanel('dice')}
            className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20 
                     hover:bg-white/20 transition-all text-white font-body text-sm"
          >
            🎲 Dice Roller
          </button>
        </div>

        {/* Center - Messages Area */}
        <div className="flex-1 flex flex-col p-6">
          {/* Character Header */}
          {character && (
            <div className="mb-4 p-4 bg-white/10 backdrop-blur-md rounded-lg border border-white/20">
              <h1 className="font-display text-2xl text-white">
                {character.name}
              </h1>
              <p className="text-sm text-white/80 font-body">
                Level {character.level} {character.race} {character.character_class}
              </p>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`p-4 rounded-lg backdrop-blur-md ${
                  message.role === 'user'
                    ? 'bg-accent-400/20 border border-accent-400/30 ml-12'
                    : 'bg-white/10 border border-white/20 mr-12'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-display text-sm text-white">
                    {message.role === 'user' ? 'You' : 'Dungeon Master'}
                  </span>
                  {message.role === 'assistant' && (
                    <span className="text-xs font-body font-bold uppercase tracking-wide 
                                   bg-accent-400 text-primary-900 px-2 py-0.5 rounded">
                      AI
                    </span>
                  )}
                </div>
                <p className="text-narrative text-white font-body leading-relaxed whitespace-pre-line">
                  {message.content}
                </p>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={sendMessage} className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Describe your action..."
              disabled={isLoading}
              className="flex-1 bg-white/10 backdrop-blur-md border-white/20 text-white 
                       placeholder:text-white/50 font-body"
            />
            <Button 
              type="submit" 
              disabled={isLoading}
              className="font-body"
            >
              {isLoading ? 'Sending...' : 'Send'}
            </Button>
          </form>
        </div>

        {/* Right Panel - Expanded Content */}
        {openPanel && (
          <div className="w-96 p-6 bg-white/10 backdrop-blur-xl border-l border-white/20 overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-xl text-white">
                {openPanel === 'stats' && '⚔️ Character Stats'}
                {openPanel === 'inventory' && '🎒 Inventory'}
                {openPanel === 'dice' && '🎲 Dice Roller'}
              </h2>
              <button
                onClick={() => setOpenPanel(null)}
                className="text-white/60 hover:text-white text-2xl"
              >
                ×
              </button>
            </div>

            {/* Stats Panel */}
            {openPanel === 'stats' && character && (
              <div className="space-y-4">
                <Card className="bg-white/5 border-white/10">
                  <CardContent className="p-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-white/60 font-body uppercase">HP</p>
                        <p className="text-lg font-bold text-success-500">
                          {character.hp_current} / {character.hp_max}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-white/60 font-body uppercase">Level</p>
                        <p className="text-lg font-bold text-white">{character.level}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <div className="space-y-3">
                  <h3 className="font-body text-sm text-white/80 uppercase tracking-wide">Ability Scores</h3>
                  {[
                    { name: 'Strength', value: character.strength },
                    { name: 'Dexterity', value: character.dexterity },
                    { name: 'Constitution', value: character.constitution },
                    { name: 'Intelligence', value: character.intelligence },
                    { name: 'Wisdom', value: character.wisdom },
                    { name: 'Charisma', value: character.charisma },
                  ].map(({ name, value }) => (
                    <div key={name} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                      <span className="font-body text-white">{name}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-white font-bold">{value}</span>
                        <span className="text-accent-400 font-mono text-sm">
                          {calculateModifier(value) >= 0 ? '+' : ''}{calculateModifier(value)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Inventory Panel */}
            {openPanel === 'inventory' && (
              <div className="text-white/60 font-body text-center py-8">
                Inventory system coming soon...
              </div>
            )}

            {/* Dice Panel */}
            {openPanel === 'dice' && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm text-white/80 font-body">Dice Notation</label>
                  <Input
                    value={diceNotation}
                    onChange={(e) => setDiceNotation(e.target.value)}
                    placeholder="e.g., 1d20, 2d6+3"
                    className="bg-white/5 border-white/10 text-white font-mono"
                  />
                </div>

                <div className="grid grid-cols-3 gap-2">
                  {['1d4', '1d6', '1d8', '1d10', '1d12', '1d20'].map((notation) => (
                    <Button
                      key={notation}
                      variant="outline"
                      onClick={() => {
                        setDiceNotation(notation);
                        setLastDiceResult(null);
                      }}
                      className="font-mono border-white/20 text-white hover:bg-white/10"
                    >
                      {notation}
                    </Button>
                  ))}
                </div>

                <Button 
                  onClick={rollDice} 
                  className="w-full font-body"
                  size="lg"
                >
                  Roll Dice
                </Button>

                {lastDiceResult && (
                  <Card className="bg-accent-400/20 border-accent-400/30">
                    <CardContent className="p-4">
                      <div className="text-center">
                        <p className="text-sm text-white/80 font-body mb-2">
                          {lastDiceResult.notation}
                        </p>
                        <p className="text-4xl font-bold text-accent-400 font-display mb-2">
                          {lastDiceResult.total}
                        </p>
                        {lastDiceResult.individual_rolls && (
                          <p className="text-xs text-white/60 font-mono">
                            Rolls: {lastDiceResult.individual_rolls.map((r: any) => r.roll).join(', ')}
                            {lastDiceResult.modifier !== 0 && ` (${lastDiceResult.modifier >= 0 ? '+' : ''}${lastDiceResult.modifier})`}
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
