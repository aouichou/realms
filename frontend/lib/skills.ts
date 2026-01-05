/**
 * D&D 5e Skills System
 * All 18 core skills with their associated ability scores
 */

export type AbilityScore = 'strength' | 'dexterity' | 'constitution' | 'intelligence' | 'wisdom' | 'charisma';

export type SkillName =
	| 'Acrobatics'
	| 'Animal Handling'
	| 'Arcana'
	| 'Athletics'
	| 'Deception'
	| 'History'
	| 'Insight'
	| 'Intimidation'
	| 'Investigation'
	| 'Medicine'
	| 'Nature'
	| 'Perception'
	| 'Performance'
	| 'Persuasion'
	| 'Religion'
	| 'Sleight of Hand'
	| 'Stealth'
	| 'Survival';

export interface Skill {
	name: SkillName;
	ability: AbilityScore;
	description: string;
}

/**
 * All 18 D&D 5e skills with their ability score mappings
 */
export const SKILLS: Skill[] = [
	{
		name: 'Acrobatics',
		ability: 'dexterity',
		description: 'Balance, tumbling, and staying on your feet in tricky situations',
	},
	{
		name: 'Animal Handling',
		ability: 'wisdom',
		description: 'Calming, training, and controlling animals',
	},
	{
		name: 'Arcana',
		ability: 'intelligence',
		description: 'Knowledge of magic, spells, and magical items',
	},
	{
		name: 'Athletics',
		ability: 'strength',
		description: 'Climbing, jumping, swimming, and feats of physical strength',
	},
	{
		name: 'Deception',
		ability: 'charisma',
		description: 'Lying, disguising intentions, and misleading others',
	},
	{
		name: 'History',
		ability: 'intelligence',
		description: 'Knowledge of historical events, legends, and past cultures',
	},
	{
		name: 'Insight',
		ability: 'wisdom',
		description: 'Reading intentions, detecting lies, and understanding motives',
	},
	{
		name: 'Intimidation',
		ability: 'charisma',
		description: 'Threatening, coercing, and instilling fear in others',
	},
	{
		name: 'Investigation',
		ability: 'intelligence',
		description: 'Finding clues, deducing information, and solving puzzles',
	},
	{
		name: 'Medicine',
		ability: 'wisdom',
		description: 'Stabilizing the dying, diagnosing illness, and treating wounds',
	},
	{
		name: 'Nature',
		ability: 'intelligence',
		description: 'Knowledge of terrain, plants, animals, and weather',
	},
	{
		name: 'Perception',
		ability: 'wisdom',
		description: 'Spotting, hearing, and detecting the presence of something',
	},
	{
		name: 'Performance',
		ability: 'charisma',
		description: 'Entertaining, acting, dancing, or playing music',
	},
	{
		name: 'Persuasion',
		ability: 'charisma',
		description: 'Influencing others diplomatically, friendly, or tactfully',
	},
	{
		name: 'Religion',
		ability: 'intelligence',
		description: 'Knowledge of deities, rites, prayers, and religious hierarchies',
	},
	{
		name: 'Sleight of Hand',
		ability: 'dexterity',
		description: 'Picking pockets, hiding objects, and manual trickery',
	},
	{
		name: 'Stealth',
		ability: 'dexterity',
		description: 'Hiding, moving silently, and avoiding detection',
	},
	{
		name: 'Survival',
		ability: 'wisdom',
		description: 'Tracking, foraging, and navigating wilderness',
	},
];

/**
 * Class-specific skill proficiency rules from D&D 5e
 */
export interface ClassSkillRules {
	count: number; // Number of skills to choose
	choices: SkillName[]; // Available skills for the class
}

export const CLASS_SKILL_PROFICIENCIES: Record<string, ClassSkillRules> = {
	Barbarian: {
		count: 2,
		choices: ['Animal Handling', 'Athletics', 'Intimidation', 'Nature', 'Perception', 'Survival'],
	},
	Bard: {
		count: 3,
		choices: [
			'Acrobatics',
			'Animal Handling',
			'Arcana',
			'Athletics',
			'Deception',
			'History',
			'Insight',
			'Intimidation',
			'Investigation',
			'Medicine',
			'Nature',
			'Perception',
			'Performance',
			'Persuasion',
			'Religion',
			'Sleight of Hand',
			'Stealth',
			'Survival',
		],
	},
	Cleric: {
		count: 2,
		choices: ['History', 'Insight', 'Medicine', 'Persuasion', 'Religion'],
	},
	Druid: {
		count: 2,
		choices: [
			'Arcana',
			'Animal Handling',
			'Insight',
			'Medicine',
			'Nature',
			'Perception',
			'Religion',
			'Survival',
		],
	},
	Fighter: {
		count: 2,
		choices: [
			'Acrobatics',
			'Animal Handling',
			'Athletics',
			'History',
			'Insight',
			'Intimidation',
			'Perception',
			'Survival',
		],
	},
	Monk: {
		count: 2,
		choices: ['Acrobatics', 'Athletics', 'History', 'Insight', 'Religion', 'Stealth'],
	},
	Paladin: {
		count: 2,
		choices: ['Athletics', 'Insight', 'Intimidation', 'Medicine', 'Persuasion', 'Religion'],
	},
	Ranger: {
		count: 3,
		choices: [
			'Animal Handling',
			'Athletics',
			'Insight',
			'Investigation',
			'Nature',
			'Perception',
			'Stealth',
			'Survival',
		],
	},
	Rogue: {
		count: 4,
		choices: [
			'Acrobatics',
			'Athletics',
			'Deception',
			'Insight',
			'Intimidation',
			'Investigation',
			'Perception',
			'Performance',
			'Persuasion',
			'Sleight of Hand',
			'Stealth',
		],
	},
	Sorcerer: {
		count: 2,
		choices: ['Arcana', 'Deception', 'Insight', 'Intimidation', 'Persuasion', 'Religion'],
	},
	Warlock: {
		count: 2,
		choices: [
			'Arcana',
			'Deception',
			'History',
			'Intimidation',
			'Investigation',
			'Nature',
			'Religion',
		],
	},
	Wizard: {
		count: 2,
		choices: ['Arcana', 'History', 'Insight', 'Investigation', 'Medicine', 'Religion'],
	},
};

/**
 * Racial skill bonuses from D&D 5e
 */
export interface RacialSkillBonus {
	skills: SkillName[]; // Fixed skills granted
	chooseCount?: number; // Number of skills to choose (e.g., Half-Elf)
	chooseFrom?: SkillName[]; // Available choices (if chooseCount > 0)
}

export const RACIAL_SKILL_BONUSES: Record<string, RacialSkillBonus> = {
	Elf: {
		skills: ['Perception'],
	},
	'Half-Elf': {
		skills: [],
		chooseCount: 2,
		chooseFrom: [
			'Acrobatics',
			'Animal Handling',
			'Arcana',
			'Athletics',
			'Deception',
			'History',
			'Insight',
			'Intimidation',
			'Investigation',
			'Medicine',
			'Nature',
			'Perception',
			'Performance',
			'Persuasion',
			'Religion',
			'Sleight of Hand',
			'Stealth',
			'Survival',
		],
	},
	// Most other races don't grant skill proficiencies, just tool proficiencies
	Dwarf: {
		skills: [],
	},
	Halfling: {
		skills: [],
	},
	Human: {
		skills: [],
	},
	Dragonborn: {
		skills: [],
	},
	Gnome: {
		skills: [],
	},
	'Half-Orc': {
		skills: [],
	},
	Tiefling: {
		skills: [],
	},
};

/**
 * Calculate ability modifier from ability score
 */
export function getAbilityModifier(score: number): number {
	return Math.floor((score - 10) / 2);
}

/**
 * Calculate skill bonus (ability modifier + proficiency bonus if proficient)
 */
export function calculateSkillBonus(
	abilityScore: number,
	isProficient: boolean,
	proficiencyBonus: number
): number {
	const abilityMod = getAbilityModifier(abilityScore);
	return isProficient ? abilityMod + proficiencyBonus : abilityMod;
}

/**
 * Get proficiency bonus by character level (D&D 5e rules)
 */
export function getProficiencyBonus(level: number): number {
	if (level <= 4) return 2;
	if (level <= 8) return 3;
	if (level <= 12) return 4;
	if (level <= 16) return 5;
	return 6;
}
