/**
 * Conditional logger that only logs in development
 * Prevents sensitive information from appearing in production console
 */

const isDevelopment = process.env.NODE_ENV !== 'production';

export const logger = {
	/**
	 * Log debug information (only in development)
	 */
	debug(...args: any[]) {
		if (isDevelopment) {
			console.log('[DEBUG]', ...args);
		}
	},

	/**
	 * Log informational messages (only in development)
	 */
	info(...args: any[]) {
		if (isDevelopment) {
			console.info('[INFO]', ...args);
		}
	},

	/**
	 * Log warnings (always shown)
	 */
	warn(...args: any[]) {
		console.warn('[WARN]', ...args);
	},

	/**
	 * Log errors (always shown)
	 */
	error(...args: any[]) {
		console.error('[ERROR]', ...args);
	},

	/**
	 * Conditional log - only in development
	 * Use for temporary debugging
	 */
	log(...args: any[]) {
		if (isDevelopment) {
			console.log(...args);
		}
	},
};

/**
 * Log only in development (convenience function)
 */
export function devLog(...args: any[]) {
	if (isDevelopment) {
		console.log(...args);
	}
}
