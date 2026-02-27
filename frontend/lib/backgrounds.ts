/**
 * D&D 5e Backgrounds
 * Contains all official backgrounds with their descriptions and skill proficiencies
 */

export interface Background {
	name: string;
	description: string;
	skillProficiencies: string[];
	feature: string;
	featureDescription: string;
}

export const BACKGROUNDS: Background[] = [
	{
		name: 'Acolyte',
		description: 'You have spent your life in the service of a temple to a specific god or pantheon of gods. You act as an intermediary between the realm of the holy and the mortal world, performing sacred rites and offering sacrifices in order to conduct worshipers into the presence of the divine.',
		skillProficiencies: ['Insight', 'Religion'],
		feature: 'Shelter of the Faithful',
		featureDescription: 'You and your companions can receive free healing and care at a temple, shrine, or other established presence of your faith. Those who share your religion will support you at a modest lifestyle.',
	},
	{
		name: 'Charlatan',
		description: 'You have always had a way with people. You know what makes them tick, you can tease out their hearts\' desires after a few minutes of conversation, and with a few leading questions you can read them like they were children\'s books.',
		skillProficiencies: ['Deception', 'Sleight of Hand'],
		feature: 'False Identity',
		featureDescription: 'You have created a second identity that includes documentation, established acquaintances, and disguises. You can forge documents including official papers and personal letters.',
	},
	{
		name: 'Criminal',
		description: 'You are an experienced criminal with a history of breaking the law. You have spent a lot of time among other criminals and still have contacts within the criminal underworld.',
		skillProficiencies: ['Deception', 'Stealth'],
		feature: 'Criminal Contact',
		featureDescription: 'You have a reliable and trustworthy contact who acts as your liaison to a network of other criminals. You can get messages to and from your contact even over great distances.',
	},
	{
		name: 'Entertainer',
		description: 'You thrive in front of an audience. You know how to entrance them, entertain them, and even inspire them. Your poetics can stir the hearts of those who hear you, awakening grief or joy, laughter or anger.',
		skillProficiencies: ['Acrobatics', 'Performance'],
		feature: 'By Popular Demand',
		featureDescription: 'You can always find a place to perform, usually in an inn or tavern but possibly with a circus, at a theater, or even in a noble\'s court. You receive free lodging and food of a modest or comfortable standard.',
	},
	{
		name: 'Folk Hero',
		description: 'You come from a humble social rank, but you are destined for so much more. Already the people of your home village regard you as their champion, and your destiny calls you to stand against the tyrants and monsters that threaten the common folk everywhere.',
		skillProficiencies: ['Animal Handling', 'Survival'],
		feature: 'Rustic Hospitality',
		featureDescription: 'Since you come from the ranks of the common folk, you fit in among them with ease. You can find a place to hide, rest, or recuperate among other commoners, unless you have shown yourself to be a danger to them.',
	},
	{
		name: 'Guild Artisan',
		description: 'You are a member of an artisan\'s guild, skilled in a particular field and closely associated with other artisans. You are a well-established part of the mercantile world, freed by talent and wealth from the constraints of a feudal social order.',
		skillProficiencies: ['Insight', 'Persuasion'],
		feature: 'Guild Membership',
		featureDescription: 'As an established and respected member of a guild, you can rely on certain benefits that membership provides. Your fellow guild members will provide you with lodging and food if necessary, and pay for your funeral if needed.',
	},
	{
		name: 'Hermit',
		description: 'You lived in seclusion—either in a sheltered community such as a monastery, or entirely alone—for a formative part of your life. In your time apart from the clamor of society, you found quiet, solitude, and perhaps some of the answers you were looking for.',
		skillProficiencies: ['Medicine', 'Religion'],
		feature: 'Discovery',
		featureDescription: 'The quiet seclusion of your extended hermitage gave you access to a unique and powerful discovery. The exact nature of this revelation depends on the nature of your seclusion.',
	},
	{
		name: 'Noble',
		description: 'You understand wealth, power, and privilege. You carry a noble title, and your family owns land, collects taxes, and wields significant political influence. You might be a pampered aristocrat unfamiliar with work or discomfort, a former merchant just elevated to the nobility, or a disinherited scoundrel.',
		skillProficiencies: ['History', 'Persuasion'],
		feature: 'Position of Privilege',
		featureDescription: 'Thanks to your noble birth, people are inclined to think the best of you. You are welcome in high society, and people assume you have the right to be wherever you are.',
	},
	{
		name: 'Outlander',
		description: 'You grew up in the wilds, far from civilization and the comforts of town and technology. You\'ve witnessed the migration of herds larger than forests, survived weather more extreme than any city-dweller could comprehend, and enjoyed the solitude of being the only thinking creature for miles in any direction.',
		skillProficiencies: ['Athletics', 'Survival'],
		feature: 'Wanderer',
		featureDescription: 'You have an excellent memory for maps and geography, and you can always recall the general layout of terrain, settlements, and other features around you. You can find food and fresh water for yourself and up to five other people each day.',
	},
	{
		name: 'Sage',
		description: 'You spent years learning the lore of the multiverse. You scoured manuscripts, studied scrolls, and listened to the greatest experts on the subjects that interest you. Your efforts have made you a master in your fields of study.',
		skillProficiencies: ['Arcana', 'History'],
		feature: 'Researcher',
		featureDescription: 'When you attempt to learn or recall a piece of lore, if you do not know that information, you often know where and from whom you can obtain it. Usually, this information comes from a library, scriptorium, university, or a sage or other learned person or creature.',
	},
	{
		name: 'Sailor',
		description: 'You sailed on a seagoing vessel for years. In that time, you faced down mighty storms, monsters of the deep, and those who wanted to sink your craft to the bottomless depths. Your first love is the distant line of the horizon, but the time has come to try your hand at something new.',
		skillProficiencies: ['Athletics', 'Perception'],
		feature: 'Ship\'s Passage',
		featureDescription: 'When you need to, you can secure free passage on a sailing ship for yourself and your companions. You might sail on the ship you served on, or another ship you have good relations with.',
	},
	{
		name: 'Soldier',
		description: 'War has been your life for as long as you care to remember. You trained as a youth, studied the use of weapons and armor, learned basic survival techniques, including how to stay alive on the battlefield. You might have been part of a standing national army or a mercenary company.',
		skillProficiencies: ['Athletics', 'Intimidation'],
		feature: 'Military Rank',
		featureDescription: 'You have a military rank from your career as a soldier. Soldiers loyal to your former military organization still recognize your authority and influence, and they defer to you if they are of a lower rank.',
	},
	{
		name: 'Urchin',
		description: 'You grew up on the streets alone, orphaned, and poor. You had no one to watch over you or to provide for you, so you learned to provide for yourself. You fought fiercely over food and kept a constant watch out for other desperate souls who might steal from you.',
		skillProficiencies: ['Sleight of Hand', 'Stealth'],
		feature: 'City Secrets',
		featureDescription: 'You know the secret patterns and flow of cities and can find passages through the urban sprawl that others would miss. When you are not in combat, you and your companions can travel between any two locations in the city twice as fast as your speed would normally allow.',
	},
	{
		name: 'Knight',
		description: 'You are a noble warrior who has sworn oaths of service to a lord, monarch, or military order. You carry the honor of knighthood, trained in the arts of war and chivalry. Your code dictates how you must conduct yourself, and you uphold these ideals with your very life.',
		skillProficiencies: ['History', 'Persuasion'],
		feature: 'Retainers',
		featureDescription: 'You have the service of three retainers loyal to your family. These retainers can be attendants or messengers, and one might be a majordomo. Your retainers are commoners who can perform mundane tasks for you, but they do not fight for you.',
	},
	{
		name: 'Pirate',
		description: 'You spent your youth under the sway of a dread pirate, a ruthless cutthroat who taught you how to survive in a world of sharks and savages. You\'ve indulged in larceny on the high seas and sent more than one deserving soul to a briny grave.',
		skillProficiencies: ['Athletics', 'Perception'],
		feature: 'Bad Reputation',
		featureDescription: 'No matter where you go, people are afraid of you due to your reputation. When you are in a civilized settlement, you can get away with minor criminal offenses, such as refusing to pay for food at a tavern or breaking down doors at a local shop.',
	},
	{
		name: 'Spy',
		description: 'You have always had a talent for subterfuge and information gathering. You might have been an agent for a government, a corporate entity, or a freelance operative selling your services to the highest bidder. Your work has taken you to dangerous places, and you\'ve learned to trust your instincts.',
		skillProficiencies: ['Deception', 'Stealth'],
		feature: 'Covert Operations',
		featureDescription: 'You have reliable contacts within intelligence networks who can provide you with information or help arrange covert meetings. You know how to use dead drops, coded messages, and other tradecraft techniques.',
	},
	{
		name: 'City Watch',
		description: 'You have served the community where you grew up, standing as its first line of defense against crime. You aren\'t a soldier, directing your gaze outward at possible enemies. Instead, your service to your hometown was to help police its populace, protecting the citizenry from lawbreakers and malefactors of every stripe.',
		skillProficiencies: ['Athletics', 'Insight'],
		feature: 'Watcher\'s Eye',
		featureDescription: 'Your experience in enforcing the law, and dealing with lawbreakers, gives you a feel for local laws and criminals. You can easily find the local outpost of the watch or similar organization, and just as easily pick out the dens of criminal activity in a community.',
	},
	{
		name: 'Clan Crafter',
		description: 'You are part of a respected dwarven clan or similar close-knit artisan community. You have been trained in the ancient techniques of your craft, passed down through generations. Your work is your pride, and your clan is your family.',
		skillProficiencies: ['History', 'Insight'],
		feature: 'Respect of the Craft',
		featureDescription: 'You are well established in the craft community. When you are in a settlement with members of your craft, you can find lodging and food if your funds are low. Members of your craft will assist you in finding buyers for your goods.',
	},
	{
		name: 'Cloistered Scholar',
		description: 'As a child, you were inquisitive when your playmates were possessive or raucous. In your formative years, you found your way to one of the great institutes of learning, where you were apprenticed and taught that knowledge is a more valuable treasure than gold or gems.',
		skillProficiencies: ['History', 'Religion'],
		feature: 'Library Access',
		featureDescription: 'You have access to the libraries and repositories of knowledge maintained by your institution. You know where to find most information, and you have friends among the scholars and librarians who can help you find obscure knowledge.',
	},
	{
		name: 'Far Traveler',
		description: 'You come from a distant land, unfamiliar to most people in the region where your adventure begins. Perhaps you were born on a far continent, or perhaps you spent years traveling through exotic lands. Either way, you are an outsider, and you bring with you the customs and perspectives of a different culture.',
		skillProficiencies: ['Insight', 'Perception'],
		feature: 'All Eyes on You',
		featureDescription: 'Your accent, mannerisms, figures of speech, and perhaps even your appearance all mark you as foreign. Curious glances are directed your way wherever you go, which can be a nuisance, but you also gain the friendly interest of scholars and others intrigued by far-off lands.',
	},
];

