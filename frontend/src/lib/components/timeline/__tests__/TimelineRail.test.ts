import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, cleanup, screen, fireEvent } from '@testing-library/svelte';
import TimelineRail from '../TimelineRail.svelte';
import type { TimelineEvent } from '$lib/api-types';

function createEvent(
	overrides: Partial<TimelineEvent> = {}
): TimelineEvent {
	return {
		id: `evt-${Math.random().toString(36).slice(2)}`,
		timestamp: '2026-01-08T12:00:00Z',
		event_type: 'tool_call',
		title: 'Bash tool',
		actor: 'main',
		actor_type: 'main',
		metadata: {},
		...overrides,
	};
}

describe('TimelineRail - Token Usage in Popup', () => {
	afterEach(() => {
		cleanup();
		vi.restoreAllMocks();
	});

	// =============================================================================
	// Basic rendering
	// =============================================================================

	describe('Basic rendering', () => {
		it('renders without error with events', () => {
			const events = [
				createEvent({
					metadata: { input_tokens: 1000, output_tokens: 500 },
				}),
			];

			expect(() => {
				render(TimelineRail, { props: { events } });
			}).not.toThrow();
		});

		it('renders without error with empty events array', () => {
			expect(() => {
				render(TimelineRail, { props: { events: [] } });
			}).not.toThrow();
		});
	});

	// =============================================================================
	// Token info display (popup description)
	// =============================================================================

	describe('Token info in popup', () => {
		it('handles event with input_tokens without error', () => {
			const events = [
				createEvent({
					metadata: { input_tokens: 1000 },
				}),
			];

			render(TimelineRail, { props: { events } });
			// Component renders without error
			expect(() => render(TimelineRail, { props: { events } })).not.toThrow();
		});

		it('handles event with output_tokens without error', () => {
			const events = [
				createEvent({
					metadata: { output_tokens: 500 },
				}),
			];

			render(TimelineRail, { props: { events } });
			expect(() => render(TimelineRail, { props: { events } })).not.toThrow();
		});

		it('handles event with all token fields', () => {
			const events = [
				createEvent({
					metadata: {
						input_tokens: 1000,
						output_tokens: 500,
						cache_read_input_tokens: 300,
						cache_creation_input_tokens: 200,
						cost_usd: 0.015,
					},
				}),
			];

			render(TimelineRail, { props: { events } });
			expect(() => render(TimelineRail, { props: { events } })).not.toThrow();
		});
	});

	// =============================================================================
	// Edge cases
	// =============================================================================

	describe('Edge cases', () => {
		it('handles missing metadata', () => {
			const events = [
				createEvent({
					metadata: undefined as any,
				}),
			];

			expect(() => {
				render(TimelineRail, { props: { events } });
			}).not.toThrow();
		});

		it('handles zero token values', () => {
			const events = [
				createEvent({
					metadata: {
						input_tokens: 0,
						output_tokens: 0,
						cache_read_input_tokens: 0,
						cache_creation_input_tokens: 0,
						cost_usd: 0,
					},
				}),
			];

			expect(() => {
				render(TimelineRail, { props: { events } });
			}).not.toThrow();
		});

		it('handles large cache token numbers', () => {
			const events = [
				createEvent({
					metadata: {
						cache_read_input_tokens: 150000,
					},
				}),
			];

			expect(() => {
				render(TimelineRail, { props: { events } });
			}).not.toThrow();
		});

		it('handles multiple events with different token values', () => {
			const events = [
				createEvent({
					id: 'evt-1',
					metadata: { input_tokens: 1000 },
				}),
				createEvent({
					id: 'evt-2',
					metadata: { output_tokens: 500 },
				}),
				createEvent({
					id: 'evt-3',
					metadata: { input_tokens: 800, output_tokens: 400 },
				}),
			];

			expect(() => {
				render(TimelineRail, { props: { events } });
			}).not.toThrow();
		});
	});
});