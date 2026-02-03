import { useEffect, useState } from "react";

export type Language = "en" | "fr";

// Define translations directly as TypeScript objects
const translations: Record<Language, any> = {
	en: {
		home: {
			title: "Mistral Realms",
			subtitle: "AI-Powered D&D Adventures",
			description1: "Embark on epic adventures guided by an AI Dungeon Master powered by Mistral AI.",
			description2: "Create your character, make choices, and watch your story unfold in real-time with true randomness for dice rolls.",
			signIn: "Sign In",
			register: "Register",
			login: "Login",
			tryDemo: "Try Demo",
			or: "or",
			noEmailRequired: "No email required for demo • All progress auto-saved • Claim account anytime",
			features: {
				classes: {
					title: "12 D&D Classes",
					description: "Choose from Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, or Wizard"
				},
				randomness: {
					title: "True Randomness",
					description: "Dice rolls powered by Random.org's atmospheric noise for genuine unpredictability"
				},
				aiDM: {
					title: "AI Dungeon Master",
					description: "Mistral AI creates dynamic narratives, generates scene images, and responds to your choices"
				}
			},
			footer: "Built for the Mistral AI Internship Application"
		},
		auth: {
			login: {
				title: "Welcome Back",
				subtitle: "Sign in to continue your adventure",
				email: "Email",
				password: "Password",
				emailPlaceholder: "your@email.com",
				passwordPlaceholder: "••••••••",
				signIn: "Sign In",
				signingIn: "Signing in...",
				orContinueAs: "Or continue as",
				guestMode: "Guest Mode",
				noAccount: "Don't have an account?",
				registerHere: "Register here",
				welcomeBack: "Welcome back!",
				welcomeAdventurer: "Welcome, adventurer!",
				loginFailed: "Login failed",
				guestFailed: "Failed to create guest account"
			},
			register: {
				title: "Create Account",
				subtitle: "Register to save your progress",
				email: "Email",
				username: "Username",
				password: "Password",
				confirmPassword: "Confirm Password",
				emailPlaceholder: "your@email.com",
				usernamePlaceholder: "adventurer",
				passwordPlaceholder: "••••••••",
				createAccount: "Create Account",
				creatingAccount: "Creating Account...",
				haveAccount: "Already have an account?",
				signInHere: "Sign in here",
				agreementText: "By registering, you agree to save your game progress and characters.",
				accountCreated: "Account created successfully!",
				passwordMismatch: "Passwords do not match",
				registerFailed: "Registration failed"
			}
		},
		demo: {
			title: "Mistral Realms",
			subtitle: "An AI-powered D&D adventure game",
			quickStart: {
				title: "Quick Start Demo",
				description: "Jump right into action",
				prebuiltCharacter: "Pre-built Level 2 Fighter character",
				instantGameplay: "Instant gameplay with no setup",
				aiStory: "AI-generated story & images",
				button: "Start Demo (30 sec)",
				estimatedTime: "30 sec"
			},
			customCharacter: {
				title: "Create Your Hero",
				description: "Build your own character",
				chooseRace: "Choose your race",
				chooseClass: "Choose your class (12 options)",
				customizeStats: "Customize stats & background",
				button: "Create Character (5 min)",
				estimatedTime: "5 min"
			},
			afterDemo: "After playing the demo, create your own character and use our",
			aiWizard: "AI Adventure Wizard",
			toGenerate: "to generate a custom adventure tailored to your hero!",
			haveAccount: "Already have an account?",
			loginHere: "Login here",
			creatingDemo: "Creating demo...",
			welcomeCreate: "Welcome! Create your character."
		},
		game: {
			panels: {
				stats: "⚔️ Character Stats",
				inventory: "🎒 Inventory",
				combat: "⚔️ Combat",
				spells: "✨ Spells",
				checks: "🎲 Ability Checks",
				companion: "🐾 Companion",
				images: "🖼️ Image Gallery",
				dice: "🎲 Dice Roller"
			},
			level: "Level",
			diceRoller: {
				notation: "Dice Notation",
				placeholder: "e.g., 1d20, 2d6+3",
				rollDice: "Roll Dice",
				rolls: "Rolls:"
			},
			startScreen: {
				title: "Ready to Begin?",
				description: "Your adventure awaits! Click the button below to start your journey with the AI Dungeon Master.",
				startButton: "Start Session",
				starting: "Starting..."
			},
			dmThinking: "The DM is thinking...",
			saveGame: "Save Game",
			inventory: {
				title: "Inventory",
				carryingCapacity: "Carrying Capacity",
				filterBy: "Filter by type",
				allItems: "All Items",
				weapons: "Weapons",
				armor: "Armor",
				consumables: "Consumables",
				questItems: "Quest Items",
				miscellaneous: "Miscellaneous",
				sortBy: "Sort by",
				sortName: "Name (A-Z)",
				sortType: "Type",
				sortWeight: "Weight (Low-High)",
				sortValue: "Value (High-Low)",
				noItems: "No items in inventory",
				lbs: "lbs",
				lb: "lb",
				gp: "gp",
				equipped: "Equipped",
				weight: "Weight",
				value: "Value",
				quantity: "Quantity",
				status: "Status",
				inInventory: "In Inventory",
				properties: "Properties",
				equip: "Equip",
				unequip: "Unequip",
				dropItem: "Drop Item"
			},
			spells: {
				title: "Spells",
				spellSlots: "Spell Slots",
				allLevels: "All Levels",
				allSchools: "All Schools",
				cantrips: "Cantrips",
				prepareSpells: "Prepare Spells",
				longRest: "Long Rest",
				preparedOnly: "Prepared Only",
				cast: "Cast",
				cancel: "Cancel",
				savePrepared: "Save Prepared Spells",
				castSpell: "Cast Spell",
				prepared: "Prepared",
				concentration: "Concentration",
				ritual: "Ritual",
				castingTime: "Casting Time",
				range: "Range",
				duration: "Duration",
				components: "Components",
				description: "Description",
				damage: "Damage",
				savingThrow: "Saving Throw",
				requiresConcentration: "Requires Concentration",
				canBeRitual: "Can be cast as Ritual",
				cantripNoSlot: "This is a cantrip and doesn't consume spell slots.",
				consumesSlot: "This will consume a level {level} spell slot.",
				selectPrepare: "Select which spells you want to prepare for today",
				preparedCount: "Prepared: {current} / {max}",
				schools: {
					abjuration: "Abjuration",
					conjuration: "Conjuration",
					divination: "Divination",
					enchantment: "Enchantment",
					evocation: "Evocation",
					illusion: "Illusion",
					necromancy: "Necromancy",
					transmutation: "Transmutation"
				}
			},
			companion: {
				title: "AI Companion",
				personality: "Personality",
				trigger: "Trigger",
				messages: "Messages",
				generateSpeech: "Generate Speech",
				generating: "Generating...",
				clear: "Clear",
				autoRespond: "Auto-respond to events",
				on: "ON",
				off: "OFF",
				noMessages: "No messages yet",
				companionWillSpeak: "Your companion will speak during key moments",
				personalities: {
					helpful: {
						name: "Helpful",
						description: "Provides tactical advice and warns of dangers"
					},
					brave: {
						name: "Brave",
						description: "Encourages heroic actions and bold strategies"
					},
					cautious: {
						name: "Cautious",
						description: "Prioritizes safety and warns about risks"
					},
					sarcastic: {
						name: "Sarcastic",
						description: "Witty and humorous commentary"
					},
					mysterious: {
						name: "Mysterious",
						description: "Cryptic hints and hidden knowledge"
					},
					scholarly: {
						name: "Scholarly",
						description: "Academic knowledge and lore"
					}
				},
				triggers: {
					combat_start: "Combat Start",
					player_low_hp: "Low HP",
					exploration: "Exploration",
					victory: "Victory",
					puzzle: "Puzzle",
					monster_encounter: "Monster",
					player_action: "Player Action",
					lore_discovery: "Lore Discovery"
				}
			},
			imageGallery: {
				title: "Scene Gallery",
				noImages: "No scene images generated yet.",
				imagesWillAppear: "Images will appear here as your adventure unfolds.",
				scene: "Scene",
				scenesCaptured: "{count} scenes captured",
				sceneCaptured: "1 scene captured"
			},
			abilityChecks: {
				title: "Ability Checks & Skills",
				quickChecks: "Quick Checks",
				rollModifiers: "Roll Modifiers",
				targetDC: "Target DC:",
				allSkills: "All Skills",
				recentRolls: "Recent Rolls",
				advantage: "Advantage",
				disadvantage: "Disadvantage",
				roll: "Roll",
				proficient: "Proficient",
				notProficient: "Not proficient",
				optional: "Optional",
				dc: "DC",
				adv: "Adv",
				dis: "Dis",
				prof: "PROF",
				rolls: "Rolls",
				skills: {
					athletics: "Athletics",
					acrobatics: "Acrobatics",
					sleightOfHand: "Sleight of Hand",
					stealth: "Stealth",
					arcana: "Arcana",
					history: "History",
					investigation: "Investigation",
					nature: "Nature",
					religion: "Religion",
					animalHandling: "Animal Handling",
					insight: "Insight",
					medicine: "Medicine",
					perception: "Perception",
					survival: "Survival",
					deception: "Deception",
					intimidation: "Intimidation",
					performance: "Performance",
					persuasion: "Persuasion"
				}
			},
			spellCasting: {
				title: "Spellcasting",
				loadingSpells: "Loading spells...",
				cantrips: "Cantrips",
				level1st: "1st Level",
				level2nd: "2nd Level",
				level3rd: "3rd Level",
				levelNth: "{level}th Level",
				cast: "Cast",
				casting: "Casting...",
				castSpell: "Cast Spell",
				concentration: "Concentration",
				ritual: "Ritual",
				upcast: "Upcast",
				upcasting: "Upcasting",
				requires: "Requires",
				gpWorthOfMaterials: "gp worth of materials",
				consumed: "(consumed)",
				perLevel: "/level",
				castSuccess: "cast successfully!",
				dealt: "Dealt",
				damage: "damage",
				asRitual: "(as ritual, +10 minutes)",
				upcastAt: "(upcast at level {level})",
				concentrationWarning: "You are already concentrating on {spell}. Casting {newSpell} will break that concentration. Continue?",
				selectSlotLevel: "Select the spell slot level to use for casting.",
				spellSlotLevel: "Spell Slot Level",
				selectSlot: "Select slot level",
				level: "Level",
				upcastingAlert: "You are upcasting this spell from level {from} to level {to}.",
				upcastingAlertExtra: "This may increase damage or other effects.",
				failedToCast: "Failed to cast spell"
			},
			spellPreparation: {
				prepareSpells: "Prepare Spells",
				currentlyPrepared: "Currently Prepared",
				cantrips: "Cantrips",
				alwaysAvailable: "Always Available",
				level: "Level",
				concentration: "Concentration",
				ritual: "Ritual",
				noSpellsInSpellbook: "No spells in your spellbook yet. Learn spells from scrolls or by leveling up.",
				saving: "Saving...",
				savePreparation: "Save Preparation",
				noSpellsPrepared: 'No spells currently prepared. Switch to the "Prepare Spells" tab to select your spells for the day.',
				loadingSpells: "Loading spells...",
				maxPreparedReached: "Maximum of {max} spells can be prepared",
				preparedSuccessfully: "Spells prepared successfully!",
				failedToPrepare: "Failed to prepare spells",
				canChangeAfterRest: "As a {class}, you can change your prepared spells after a long rest. Your spellcasting ability is",
				modifier: "modifier"
			},
			activeEffects: {
				title: "Active Effects",
				loading: "Loading...",
				noActiveEffects: "No active effects",
				concentration: "Concentration",
				permanent: "Permanent",
				untilLongRest: "Until Long Rest",
				untilShortRest: "Until Short Rest",
				round: "round",
				rounds: "rounds",
				expiringSoon: "Expiring soon",
				minute: "minute",
				minutes: "minutes",
				hour: "hour",
				hours: "hours",
				active: "Active",
				advantage: "Advantage",
				disadvantage: "Disadvantage",
				effectTypes: {
					buff: "BUFF",
					debuff: "DEBUFF",
					condition: "CONDITION",
					concentration: "CONCENTRATION"
				}
			},
			save: {
				title: 'Save Game',
				description: 'Enter a name for your save. You can load it later from the main menu.',
				saveName: 'Save Name',
				cancel: 'Cancel',
				save: 'Save',
				saving: 'Saving...',
				errorEmptyName: 'Please enter a name for your save',
				errorDuplicateName: 'A save with this name already exists. Please choose a different name.',
				errorFailedToSave: 'Failed to save game. Please try again.',
				successSaved: 'Game saved as "{saveName}"',
				errorGeneric: 'Could not save your game. Please try again.',
			},
			load: {
				title: 'Load Game',
				description: 'Select a save to continue your adventure',
				loading: 'Loading...',
				loadButton: 'Load',
				noSaves: 'No saved games found',
				noSavesHint: 'Start a new adventure to create your first save',
				location: 'Location',
				loadingMessage: 'Loading "{saveName}"...',
				errorLoadSaves: 'Could not load save files',
				errorLoadGame: 'Could not load saved game',
			},
			adventure: {
				startButton: 'Start Adventure',
				title: 'Choose Your Adventure',
				description: 'Select a preset adventure to begin your journey. Adventures are recommended for specific character levels.',
				level: 'Level',
				cancel: 'Cancel',
				beginAdventure: 'Begin Adventure',
				starting: 'Starting...',
			},
		},
		characterCreation: {
			title: 'Create Your Hero',
			subtitle: 'Forge your legend in the Mistral Realms',
			steps: {
				basicInfo: 'Basic Info',
				skills: 'Skills',
				background: 'Background',
				personality: 'Personality',
				motivation: 'Motivation',
				spells: 'Spells',
			},
			basicInfo: {
				cardTitle: 'Character Details',
				cardDescription: 'The essentials of your hero',
				characterName: 'Character Name',
				namePlaceholder: 'Enter your character\'s name',
				race: 'Race',
				selectRace: 'Select a race',
				class: 'Class',
				selectClass: 'Select a class',
				level: 'Level',
				errorNameRequired: 'Character name is required',
				errorNameTooShort: 'Name must be at least 2 characters',
			},
			abilityScores: {
				cardTitle: 'Ability Scores (Point Buy)',
				pointsRemaining: '{points} of {max} points remaining',
				scoreRangeHint: 'Scores range from 8 to 15 (before racial modifiers)',
				strength: 'Strength',
				dexterity: 'Dexterity',
				constitution: 'Constitution',
				intelligence: 'Intelligence',
				wisdom: 'Wisdom',
				charisma: 'Charisma',
			},
			preview: {
				cardTitle: 'Character Preview',
				unnamedHero: 'Unnamed Hero',
				levelRaceClass: 'Level {level} {race} {class}',
				hitPoints: 'Hit Points',
				nextButton: 'Next: Select Skills',
				creating: 'Creating...',
			},
			spells: {
				back: 'Back',
				complete: 'Complete Character Creation',
			},
			toasts: {
				enterName: 'Please enter a character name',
				nameTooShort: 'Name is too short',
				selectClass: 'Please select a class',
				selectRace: 'Please select a race',
				notAuthenticated: 'Not authenticated. Please log in or play as guest.',
				createSuccess: '{name} created successfully!',
				createFailed: 'Failed to create character',
				connectionError: 'Cannot connect to server. Please check your connection.',
				createError: 'An error occurred while creating your character.',
				skillsSuccess: 'Skills saved successfully!',
				skillsFailed: 'Failed to save skills',
				skillsError: 'Error saving skills',
				backgroundSuccess: 'Background saved successfully!',
				backgroundFailed: 'Failed to save background',
				backgroundError: 'Error saving background',
				personalitySuccess: 'Personality saved successfully!',
				personalityFailed: 'Failed to save personality',
				personalityError: 'Error saving personality',
				motivationSuccess: 'Motivation saved successfully!',
				motivationFailed: 'Failed to save motivation',
				motivationError: 'Error saving motivation',
				spellsSuccess: 'Spells saved successfully!',
				spellsError: 'Error saving spells',
				characterCreated: 'Character created! Now choose your adventure.',
			},
		},
		common: {
			cancel: 'Cancel',
			loading: 'Loading...',
			error: 'Error',
			success: 'Success',
			level: 'Level',
		},
		concentrationTracker: {
			concentrating: 'Concentrating',
			duration: 'Duration',
			elapsed: 'Elapsed',
			saveRequired: 'Concentration Save Required!',
			damageTaken: 'Took {damage} damage. DC {dc} Constitution save required.',
			rollSave: 'Roll Save',
			successMessage: 'Success! Rolled {roll} + {modifier} = {total} (DC {dc})',
			failMessage: 'Failed! Rolled {roll} + {modifier} = {total} (DC {dc}). Concentration broken!',
			concentrationInfo: 'If you take damage, make a Constitution save (DC = 10 or half damage, whichever is higher) or lose concentration.',
		},
		ritualCasting: {
			title: 'Cast {spell} as Ritual?',
			description: 'This spell can be cast as a ritual, taking longer but not consuming a spell slot.',
			normalCasting: 'Normal Casting',
			ritualCasting: 'Ritual Casting',
			benefitsTitle: 'Ritual Casting Benefits:',
			benefit1: 'Does not consume a spell slot',
			benefit2: 'Can be cast even if no spell slots available',
			benefit3: 'Must have spell prepared (or in spellbook for Wizards)',
			drawbacksTitle: 'Drawbacks:',
			drawback1: 'Takes an additional 10 minutes to cast',
			drawback2: 'Cannot be used in combat or time-sensitive situations',
			castAsRitual: 'Cast as Ritual ({time})',
			castNormally: 'Cast Normally ({time})',
			ritual: 'Ritual',
		},
		character: {
			select: {
				title: "Select Your Character",
				subtitle: "Choose a character to begin your adventure",
				loadGame: "Load Game",
				loading: "Loading characters...",
				noCharacters: "You don't have any characters yet.",
				createFirst: "Create Your First Character",
				createNew: "Create New Character",
				level: "Lvl",
				race: "Race",
				class: "Class",
				hp: "HP",
				delete: "Delete character",
				confirmDelete: "Are you sure you want to delete {name}? This action cannot be undone.",
				error: "Failed to fetch characters",
				retry: "Retry"
			}
		},
		adventure: {
			select: {
				title: "Choose Your Adventure",
				welcome: "Welcome",
				subtitle: "Select a preset adventure or create your own custom story",
				presetTab: "Preset Adventures",
				customTab: "Custom Adventure",
				beginAdventure: "Begin Adventure",
				levelLabel: "Level",
				challengingWarning: "⚠️ This adventure may be challenging for your level",
				customTitle: "Your Custom Adventures",
				created: "Created",
				aiGeneratedTitle: "AI-Generated Custom Adventure",
				aiGeneratedDescription: "Answer 3 questions and let our AI Dungeon Master create a unique adventure tailored specifically for you",
				howItWorksTitle: "How it works:",
				howItWorks1: "Choose your adventure setting (8 options)",
				howItWorks2: "Select your primary goal (8 objectives)",
				howItWorks3: "Pick the story tone (5 moods)",
				howItWorks4: "AI generates a complete 3-5 scene adventure with NPCs, encounters, and loot",
				createCustom: "Create Custom Adventure",
				backToPreset: "Back to Preset Adventures",
				adventureStarted: "Adventure started!",
				customStarting: "Custom adventure starting!",
				startFailed: "Failed to start adventure"
			}
		}
	},
	fr: {
		home: {
			title: "Mistral Realms",
			subtitle: "Aventures D&D propulsées par l'IA",
			description1: "Embarquez dans des aventures épiques guidées par un Maître du Donjon IA propulsé par Mistral AI.",
			description2: "Créez votre personnage, faites des choix et regardez votre histoire se dérouler en temps réel avec un véritable hasard pour les jets de dés.",
			signIn: "Se connecter",
			register: "S'inscrire",
			login: "Connexion",
			tryDemo: "Essayer la démo",
			or: "ou",
			noEmailRequired: "Aucun e-mail requis pour la démo • Toute progression auto-sauvegardée • Réclamez un compte à tout moment",
			features: {
				classes: {
					title: "12 Classes D&D",
					description: "Choisissez parmi Barbare, Barde, Clerc, Druide, Guerrier, Moine, Paladin, Rôdeur, Roublard, Ensorceleur, Occultiste ou Magicien"
				},
				randomness: {
					title: "Véritable Aléatoire",
					description: "Jets de dés alimentés par le bruit atmosphérique de Random.org pour une imprévisibilité authentique"
				},
				aiDM: {
					title: "Maître du Donjon IA",
					description: "Mistral AI crée des récits dynamiques, génère des images de scène et répond à vos choix"
				}
			},
			footer: "Créé pour la candidature au stage Mistral AI"
		},
		auth: {
			login: {
				title: "Bon Retour",
				subtitle: "Connectez-vous pour continuer votre aventure",
				email: "E-mail",
				password: "Mot de passe",
				emailPlaceholder: "votre@email.com",
				passwordPlaceholder: "••••••••",
				signIn: "Se connecter",
				signingIn: "Connexion en cours...",
				orContinueAs: "Ou continuer en tant que",
				guestMode: "Mode Invité",
				noAccount: "Vous n'avez pas de compte ?",
				registerHere: "Inscrivez-vous ici",
				welcomeBack: "Bon retour !",
				welcomeAdventurer: "Bienvenue, aventurier !",
				loginFailed: "Échec de la connexion",
				guestFailed: "Échec de la création du compte invité"
			},
			register: {
				title: "Créer un Compte",
				subtitle: "Inscrivez-vous pour sauvegarder votre progression",
				email: "E-mail",
				username: "Nom d'utilisateur",
				password: "Mot de passe",
				confirmPassword: "Confirmer le mot de passe",
				emailPlaceholder: "votre@email.com",
				usernamePlaceholder: "aventurier",
				passwordPlaceholder: "••••••••",
				createAccount: "Créer un compte",
				creatingAccount: "Création du compte...",
				haveAccount: "Vous avez déjà un compte ?",
				signInHere: "Connectez-vous ici",
				agreementText: "En vous inscrivant, vous acceptez de sauvegarder votre progression de jeu et vos personnages.",
				accountCreated: "Compte créé avec succès !",
				passwordMismatch: "Les mots de passe ne correspondent pas",
				registerFailed: "Échec de l'inscription"
			}
		},
		demo: {
			title: "Mistral Realms",
			subtitle: "Un jeu d'aventure D&D propulsé par l'IA",
			quickStart: {
				title: "Démo de Démarrage Rapide",
				description: "Plongez directement dans l'action",
				prebuiltCharacter: "Personnage Guerrier niveau 2 pré-construit",
				instantGameplay: "Jeu instantané sans configuration",
				aiStory: "Histoire et images générées par IA",
				button: "Démarrer la démo (30 sec)",
				estimatedTime: "30 sec"
			},
			customCharacter: {
				title: "Créez Votre Héros",
				description: "Construisez votre propre personnage",
				chooseRace: "Choisissez votre race",
				chooseClass: "Choisissez votre classe (12 options)",
				customizeStats: "Personnalisez les statistiques et l'historique",
				button: "Créer un personnage (5 min)",
				estimatedTime: "5 min"
			},
			afterDemo: "Après avoir joué à la démo, créez votre propre personnage et utilisez notre",
			aiWizard: "Assistant d'Aventure IA",
			toGenerate: "pour générer une aventure personnalisée adaptée à votre héros !",
			haveAccount: "Vous avez déjà un compte ?",
			loginHere: "Connectez-vous ici",
			creatingDemo: "Création de la démo...",
			welcomeCreate: "Bienvenue ! Créez votre personnage."
		},
		game: {
			panels: {
				stats: "⚔️ Statistiques du personnage",
				inventory: "🎒 Inventaire",
				combat: "⚔️ Combat",
				spells: "✨ Sorts",
				checks: "🎲 Tests de compétence",
				companion: "🐾 Compagnon",
				images: "🖼️ Galerie d'images",
				dice: "🎲 Lanceur de dés"
			},
			level: "Niveau",
			diceRoller: {
				notation: "Notation des dés",
				placeholder: "ex: 1d20, 2d6+3",
				rollDice: "Lancer les dés",
				rolls: "Lancers :"
			},
			startScreen: {
				title: "Prêt à commencer ?",
				description: "Votre aventure vous attend ! Cliquez sur le bouton ci-dessous pour commencer votre voyage avec le Maître du Donjon IA.",
				startButton: "Démarrer la session",
				starting: "Démarrage..."
			},
			dmThinking: "Le MJ réfléchit...",
			saveGame: "Sauvegarder",
			inventory: {
				title: "Inventaire",
				carryingCapacity: "Capacité de transport",
				filterBy: "Filtrer par type",
				allItems: "Tous les objets",
				weapons: "Armes",
				armor: "Armures",
				consumables: "Consommables",
				questItems: "Objets de quête",
				miscellaneous: "Divers",
				sortBy: "Trier par",
				sortName: "Nom (A-Z)",
				sortType: "Type",
				sortWeight: "Poids (Bas-Haut)",
				sortValue: "Valeur (Haut-Bas)",
				noItems: "Aucun objet dans l'inventaire",
				lbs: "lbs",
				lb: "lb",
				gp: "po",
				equipped: "Équipé",
				weight: "Poids",
				value: "Valeur",
				quantity: "Quantité",
				status: "Statut",
				inInventory: "Dans l'inventaire",
				properties: "Propriétés",
				equip: "Équiper",
				unequip: "Déséquiper",
				dropItem: "Jeter l'objet"
			},
			spells: {
				title: "Sorts",
				spellSlots: "Emplacements de sorts",
				allLevels: "Tous les niveaux",
				allSchools: "Toutes les écoles",
				cantrips: "Tours de magie",
				prepareSpells: "Préparer les sorts",
				longRest: "Repos long",
				preparedOnly: "Préparés uniquement",
				cast: "Lancer",
				cancel: "Annuler",
				savePrepared: "Sauvegarder les sorts préparés",
				castSpell: "Lancer un sort",
				prepared: "Préparé",
				concentration: "Concentration",
				ritual: "Rituel",
				castingTime: "Temps d'incantation",
				range: "Portée",
				duration: "Durée",
				components: "Composantes",
				description: "Description",
				damage: "Dégâts",
				savingThrow: "Jet de sauvegarde",
				requiresConcentration: "Nécessite la concentration",
				canBeRitual: "Peut être lancé comme rituel",
				cantripNoSlot: "Ceci est un tour de magie et ne consomme pas d'emplacement de sort.",
				consumesSlot: "Cela consommera un emplacement de sort de niveau {level}.",
				selectPrepare: "Sélectionnez les sorts que vous souhaitez préparer pour aujourd'hui",
				preparedCount: "Préparés : {current} / {max}",
				schools: {
					abjuration: "Abjuration",
					conjuration: "Invocation",
					divination: "Divination",
					enchantment: "Enchantement",
					evocation: "Évocation",
					illusion: "Illusion",
					necromancy: "Nécromancie",
					transmutation: "Transmutation"
				}
			},
			companion: {
				title: "Compagnon IA",
				personality: "Personnalité",
				trigger: "Déclencheur",
				messages: "Messages",
				generateSpeech: "Générer une réplique",
				generating: "Génération...",
				clear: "Effacer",
				autoRespond: "Répondre automatiquement aux événements",
				on: "ACTIVÉ",
				off: "DÉSACTIVÉ",
				noMessages: "Aucun message pour le moment",
				companionWillSpeak: "Votre compagnon parlera lors des moments clés",
				personalities: {
					helpful: {
						name: "Serviable",
						description: "Fournit des conseils tactiques et avertit des dangers"
					},
					brave: {
						name: "Courageux",
						description: "Encourage les actions héroïques et les stratégies audacieuses"
					},
					cautious: {
						name: "Prudent",
						description: "Privilégie la sécurité et avertit des risques"
					},
					sarcastic: {
						name: "Sarcastique",
						description: "Commentaires spirituels et humoristiques"
					},
					mysterious: {
						name: "Mystérieux",
						description: "Indices cryptiques et connaissances cachées"
					},
					scholarly: {
						name: "Érudit",
						description: "Connaissances académiques et traditions"
					}
				},
				triggers: {
					combat_start: "Début de combat",
					player_low_hp: "PV bas",
					exploration: "Exploration",
					victory: "Victoire",
					puzzle: "Énigme",
					monster_encounter: "Monstre",
					player_action: "Action du joueur",
					lore_discovery: "Découverte de traditions"
				}
			},
			imageGallery: {
				title: "Galerie de scènes",
				noImages: "Aucune image de scène générée pour le moment.",
				imagesWillAppear: "Les images apparaîtront ici au fur et à mesure de votre aventure.",
				scene: "Scène",
				scenesCaptured: "{count} scènes capturées",
				sceneCaptured: "1 scène capturée"
			},
			abilityChecks: {
				title: "Tests de caractéristique et compétences",
				quickChecks: "Tests rapides",
				rollModifiers: "Modificateurs de jet",
				targetDC: "DD cible :",
				allSkills: "Toutes les compétences",
				recentRolls: "Jets récents",
				advantage: "Avantage",
				disadvantage: "Désavantage",
				roll: "Lancer",
				proficient: "Maîtrisé",
				notProficient: "Non maîtrisé",
				optional: "Optionnel",
				dc: "DD",
				adv: "Ava",
				dis: "Dés",
				prof: "MAÎT",
				rolls: "Jets",
				skills: {
					athletics: "Athlétisme",
					acrobatics: "Acrobaties",
					sleightOfHand: "Escamotage",
					stealth: "Discrétion",
					arcana: "Arcanes",
					history: "Histoire",
					investigation: "Investigation",
					nature: "Nature",
					religion: "Religion",
					animalHandling: "Dressage",
					insight: "Perspicacité",
					medicine: "Médecine",
					perception: "Perception",
					survival: "Survie",
					deception: "Tromperie",
					intimidation: "Intimidation",
					performance: "Représentation",
					persuasion: "Persuasion"
				}
			},
			spellCasting: {
				title: "Incantation",
				loadingSpells: "Chargement des sorts...",
				cantrips: "Tours de magie",
				level1st: "Niveau 1",
				level2nd: "Niveau 2",
				level3rd: "Niveau 3",
				levelNth: "Niveau {level}",
				cast: "Lancer",
				casting: "Lancement...",
				castSpell: "Lancer le sort",
				concentration: "Concentration",
				ritual: "Rituel",
				upcast: "Surlancement",
				upcasting: "Surlancement",
				requires: "Nécessite",
				gpWorthOfMaterials: "po de composantes matérielles",
				consumed: "(consumé)",
				perLevel: "/niveau",
				castSuccess: "lancé avec succès !",
				dealt: "A infligé",
				damage: "dégâts",
				asRitual: "(en rituel, +10 minutes)",
				upcastAt: "(surlancé au niveau {level})",
				concentrationWarning: "Vous vous concentrez déjà sur {spell}. Lancer {newSpell} brisera cette concentration. Continuer ?",
				selectSlotLevel: "Sélectionnez le niveau d'emplacement de sort à utiliser pour l'incantation.",
				spellSlotLevel: "Niveau d'emplacement de sort",
				selectSlot: "Sélectionner le niveau d'emplacement",
				level: "Niveau",
				upcastingAlert: "Vous surlancez ce sort du niveau {from} au niveau {to}.",
				upcastingAlertExtra: "Cela peut augmenter les dégâts ou d'autres effets.",
				failedToCast: "Échec du lancement du sort"
			},
			spellPreparation: {
				prepareSpells: "Préparer les sorts",
				currentlyPrepared: "Actuellement préparés",
				cantrips: "Tours de magie",
				alwaysAvailable: "Toujours disponibles",
				level: "Niveau",
				concentration: "Concentration",
				ritual: "Rituel",
				noSpellsInSpellbook: "Aucun sort dans votre grimoire pour le moment. Apprenez des sorts à partir de parchemins ou en montant de niveau.",
				saving: "Enregistrement...",
				savePreparation: "Enregistrer la préparation",
				noSpellsPrepared: 'Aucun sort actuellement préparé. Passez à l\'onglet "Préparer les sorts" pour sélectionner vos sorts du jour.',
				loadingSpells: "Chargement des sorts...",
				maxPreparedReached: "Maximum de {max} sorts peuvent être préparés",
				preparedSuccessfully: "Sorts préparés avec succès !",
				failedToPrepare: "Échec de la préparation des sorts",
				canChangeAfterRest: "En tant que {class}, vous pouvez modifier vos sorts préparés après un repos long. Votre caractéristique d'incantation est",
				modifier: "modificateur"
			},
			activeEffects: {
				title: "Effets actifs",
				loading: "Chargement...",
				noActiveEffects: "Aucun effet actif",
				concentration: "Concentration",
				permanent: "Permanent",
				untilLongRest: "Jusqu'au repos long",
				untilShortRest: "Jusqu'au repos court",
				round: "round",
				rounds: "rounds",
				expiringSoon: "Expire bientôt",
				minute: "minute",
				minutes: "minutes",
				hour: "heure",
				hours: "heures",
				active: "Actif",
				advantage: "Avantage",
				disadvantage: "Désavantage",
				effectTypes: {
					buff: "BONUS",
					debuff: "MALUS",
					condition: "CONDITION",
					concentration: "CONCENTRATION"
				}
			},
			save: {
				title: 'Sauvegarder la partie',
				description: 'Entrez un nom pour votre sauvegarde. Vous pourrez la charger plus tard depuis le menu principal.',
				saveName: 'Nom de sauvegarde',
				cancel: 'Annuler',
				save: 'Sauvegarder',
				saving: 'Sauvegarde...',
				errorEmptyName: 'Veuillez entrer un nom pour votre sauvegarde',
				errorDuplicateName: 'Une sauvegarde avec ce nom existe déjà. Veuillez choisir un nom différent.',
				errorFailedToSave: 'Échec de la sauvegarde. Veuillez réessayer.',
				successSaved: 'Partie sauvegardée sous "{saveName}"',
				errorGeneric: 'Impossible de sauvegarder votre partie. Veuillez réessayer.',
			},
			load: {
				title: 'Charger une partie',
				description: 'Sélectionnez une sauvegarde pour continuer votre aventure',
				loading: 'Chargement...',
				loadButton: 'Charger',
				noSaves: 'Aucune partie sauvegardée',
				noSavesHint: 'Commencez une nouvelle aventure pour créer votre première sauvegarde',
				location: 'Lieu',
				loadingMessage: 'Chargement de "{saveName}"...',
				errorLoadSaves: 'Impossible de charger les fichiers de sauvegarde',
				errorLoadGame: 'Impossible de charger la partie sauvegardée',
			},
			adventure: {
				startButton: 'Commencer l\'aventure',
				title: 'Choisissez votre aventure',
				description: 'Sélectionnez une aventure prédéfinie pour commencer votre voyage. Les aventures sont recommandées pour des niveaux de personnage spécifiques.',
				level: 'Niveau',
				cancel: 'Annuler',
				beginAdventure: 'Commencer l\'aventure',
				starting: 'Démarrage...',
			},
		},
		characterCreation: {
			title: 'Créez votre héros',
			subtitle: 'Forgez votre légende dans les Royaumes de Mistral',
			steps: {
				basicInfo: 'Infos de base',
				skills: 'Compétences',
				background: 'Historique',
				personality: 'Personnalité',
				motivation: 'Motivation',
				spells: 'Sorts',
			},
			basicInfo: {
				cardTitle: 'Détails du personnage',
				cardDescription: 'L\'essentiel de votre héros',
				characterName: 'Nom du personnage',
				namePlaceholder: 'Entrez le nom de votre personnage',
				race: 'Race',
				selectRace: 'Sélectionnez une race',
				class: 'Classe',
				selectClass: 'Sélectionnez une classe',
				level: 'Niveau',
				errorNameRequired: 'Le nom du personnage est requis',
				errorNameTooShort: 'Le nom doit contenir au moins 2 caractères',
			},
			abilityScores: {
				cardTitle: 'Caractéristiques (Achat de points)',
				pointsRemaining: '{points} sur {max} points restants',
				scoreRangeHint: 'Les scores vont de 8 à 15 (avant modificateurs raciaux)',
				strength: 'Force',
				dexterity: 'Dextérité',
				constitution: 'Constitution',
				intelligence: 'Intelligence',
				wisdom: 'Sagesse',
				charisma: 'Charisme',
			},
			preview: {
				cardTitle: 'Aperçu du personnage',
				unnamedHero: 'Héros sans nom',
				levelRaceClass: 'Niveau {level} {race} {class}',
				hitPoints: 'Points de vie',
				nextButton: 'Suivant : Sélectionner les compétences',
				creating: 'Création...',
			},
			spells: {
				back: 'Retour',
				complete: 'Terminer la création du personnage',
			},
			toasts: {
				enterName: 'Veuillez entrer un nom de personnage',
				nameTooShort: 'Le nom est trop court',
				selectClass: 'Veuillez sélectionner une classe',
				selectRace: 'Veuillez sélectionner une race',
				notAuthenticated: 'Non authentifié. Veuillez vous connecter ou jouer en tant qu\'invité.',
				createSuccess: '{name} créé avec succès !',
				createFailed: 'Échec de la création du personnage',
				connectionError: 'Impossible de se connecter au serveur. Veuillez vérifier votre connexion.',
				createError: 'Une erreur s\'est produite lors de la création de votre personnage.',
				skillsSuccess: 'Compétences sauvegardées avec succès !',
				skillsFailed: 'Échec de la sauvegarde des compétences',
				skillsError: 'Erreur lors de la sauvegarde des compétences',
				backgroundSuccess: 'Historique sauvegardé avec succès !',
				backgroundFailed: 'Échec de la sauvegarde de l\'historique',
				backgroundError: 'Erreur lors de la sauvegarde de l\'historique',
				personalitySuccess: 'Personnalité sauvegardée avec succès !',
				personalityFailed: 'Échec de la sauvegarde de la personnalité',
				personalityError: 'Erreur lors de la sauvegarde de la personnalité',
				motivationSuccess: 'Motivation sauvegardée avec succès !',
				motivationFailed: 'Échec de la sauvegarde de la motivation',
				motivationError: 'Erreur lors de la sauvegarde de la motivation',
				spellsSuccess: 'Sorts sauvegardés avec succès !',
				spellsError: 'Erreur lors de la sauvegarde des sorts',
				characterCreated: 'Personnage créé ! Choisissez maintenant votre aventure.',
			},
		},
		common: {
			cancel: 'Annuler',
			loading: 'Chargement...',
			error: 'Erreur',
			success: 'Succès',
			level: 'Niveau',
		},
		concentrationTracker: {
			concentrating: 'Concentration',
			duration: 'Durée :',
			elapsed: 'Écoulé :',
			saveRequired: 'Jet de sauvegarde de concentration requis !',
			damageTaken: 'Dégâts subis : {damage}. Jet de sauvegarde de Constitution DD {dc} requis.',
			rollSave: 'Lancer le jet',
			successMessage: 'Succès ! ({roll} + {modifier} = {total} vs DD {dc})',
			failMessage: 'Échec ! ({roll} + {modifier} = {total} vs DD {dc}) - Concentration perdue.',
			concentrationInfo: 'Lorsque vous subissez des dégâts en maintenant une concentration, vous devez réussir un jet de sauvegarde de Constitution. Le DD est égal à 10 ou la moitié des dégâts subis, selon le plus élevé.',
		},
		ritualCasting: {
			title: 'Lancer {spell} en rituel ?',
			description: 'Ce sort peut être lancé en rituel, ce qui prend 10 minutes de plus mais ne consomme pas d\'emplacement de sort.',
			normalCasting: 'Incantation normale',
			ritualCasting: 'Incantation rituelle',
			benefitsTitle: 'Avantages de l\'incantation rituelle :',
			benefit1: 'Ne consomme pas d\'emplacement de sort',
			benefit2: 'Toujours disponible si préparé',
			benefit3: 'Conservez vos emplacements pour le combat',
			drawbacksTitle: 'Inconvénients :',
			drawback1: 'Prend 10 minutes de plus à lancer',
			drawback2: 'Ne peut pas être utilisé en combat',
			castAsRitual: 'Lancer en rituel ({time})',
			castNormally: 'Lancer normalement',
			ritual: 'Rituel',
		},
		character: {
			select: {
				title: "Sélectionnez votre personnage",
				subtitle: "Choisissez un personnage pour commencer votre aventure",
				loadGame: "Charger une partie",
				loading: "Chargement des personnages...",
				noCharacters: "Vous n'avez pas encore de personnages.",
				createFirst: "Créez votre premier personnage",
				createNew: "Créer un nouveau personnage",
				level: "Niv",
				race: "Race",
				class: "Classe",
				hp: "PV",
				delete: "Supprimer le personnage",
				confirmDelete: "Êtes-vous sûr de vouloir supprimer {name} ? Cette action est irréversible.",
				error: "Échec du chargement des personnages",
				retry: "Réessayer"
			}
		},
		adventure: {
			select: {
				title: "Choisissez votre aventure",
				welcome: "Bienvenue",
				subtitle: "Sélectionnez une aventure prédéfinie ou créez votre propre histoire personnalisée",
				presetTab: "Aventures prédéfinies",
				customTab: "Aventure personnalisée",
				beginAdventure: "Commencer l'aventure",
				levelLabel: "Niveau",
				challengingWarning: "⚠️ Cette aventure peut être difficile pour votre niveau",
				customTitle: "Vos aventures personnalisées",
				created: "Créée le",
				aiGeneratedTitle: "Aventure personnalisée générée par IA",
				aiGeneratedDescription: "Répondez à 3 questions et laissez notre Maître du Donjon IA créer une aventure unique adaptée spécialement pour vous",
				howItWorksTitle: "Comment ça marche :",
				howItWorks1: "Choisissez le cadre de votre aventure (8 options)",
				howItWorks2: "Sélectionnez votre objectif principal (8 objectifs)",
				howItWorks3: "Choisissez le ton de l'histoire (5 ambiances)",
				howItWorks4: "L'IA génère une aventure complète de 3 à 5 scènes avec PNJ, rencontres et butin",
				createCustom: "Créer une aventure personnalisée",
				backToPreset: "Retour aux aventures prédéfinies",
				adventureStarted: "Aventure commencée !",
				customStarting: "Démarrage de l'aventure personnalisée !",
				startFailed: "Échec du démarrage de l'aventure"
			}
		}
	}
};

export function useTranslation() {
	const [language, setLanguage] = useState<Language>("en");

	useEffect(() => {
		// Load saved language preference
		const savedLanguage = localStorage.getItem("dm_language") as Language;
		if (savedLanguage && (savedLanguage === "en" || savedLanguage === "fr")) {
			setLanguage(savedLanguage);
		}

		// Listen for language changes
		const handleStorageChange = (e: StorageEvent) => {
			if (e.key === "dm_language" && e.newValue) {
				const newLang = e.newValue as Language;
				if (newLang === "en" || newLang === "fr") {
					setLanguage(newLang);
				}
			}
		};

		// Listen for custom event (for same-window updates)
		const handleLanguageChange = ((e: CustomEvent) => {
			const newLang = e.detail as Language;
			if (newLang === "en" || newLang === "fr") {
				setLanguage(newLang);
			}
		}) as EventListener;

		window.addEventListener("storage", handleStorageChange);
		window.addEventListener("languageChange", handleLanguageChange);

		return () => {
			window.removeEventListener("storage", handleStorageChange);
			window.removeEventListener("languageChange", handleLanguageChange);
		};
	}, []);

	const t = (key: string): string => {
		const keys = key.split(".");
		let value: any = translations[language];

		for (const k of keys) {
			if (value && typeof value === "object") {
				value = value[k];
			} else {
				return key; // Return key if translation not found
			}
		}

		return typeof value === "string" ? value : key;
	};

	return { t, language, setLanguage };
}
