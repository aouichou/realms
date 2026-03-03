import { beforeEach, describe, expect, it } from 'vitest';
import { getHeadersWithCsrf, setCsrfTokenFromHeader } from '../csrf';

describe('CSRF utilities', () => {
	beforeEach(() => {
		// Reset document.cookie before each test
		Object.defineProperty(document, 'cookie', {
			writable: true,
			value: '',
		});
	});

	describe('getHeadersWithCsrf', () => {
		it('returns empty headers when no CSRF cookie is set', () => {
			const headers = getHeadersWithCsrf();
			expect(headers).toEqual({});
			expect(headers['X-CSRF-Token']).toBeUndefined();
		});

		it('adds CSRF token from cookie to headers', () => {
			Object.defineProperty(document, 'cookie', {
				writable: true,
				value: 'csrf_token=abc123; other_cookie=xyz',
			});

			const headers = getHeadersWithCsrf();
			expect(headers['X-CSRF-Token']).toBe('abc123');
		});

		it('merges with additional headers', () => {
			Object.defineProperty(document, 'cookie', {
				writable: true,
				value: 'csrf_token=token123',
			});

			const headers = getHeadersWithCsrf({ 'Content-Type': 'application/json' });
			expect(headers['Content-Type']).toBe('application/json');
			expect(headers['X-CSRF-Token']).toBe('token123');
		});

		it('preserves additional headers even without CSRF cookie', () => {
			const headers = getHeadersWithCsrf({ Authorization: 'Bearer xyz' });
			expect(headers['Authorization']).toBe('Bearer xyz');
		});
	});

	describe('setCsrfTokenFromHeader', () => {
		it('does not throw when header is present', () => {
			const headers = new Headers({ 'X-CSRF-Token': 'server-token' });
			expect(() => setCsrfTokenFromHeader(headers)).not.toThrow();
		});

		it('does not throw when header is absent', () => {
			const headers = new Headers();
			expect(() => setCsrfTokenFromHeader(headers)).not.toThrow();
		});
	});
});
