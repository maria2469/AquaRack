/**
 * Global state management for fleet reasoning results.
 * Shared across Dashboard, FleetView, and other components.
 * 
 * Uses module pattern to avoid circular import issues.
 */

const state = {
  fleetResult: null,
};

export function setGlobalFleetResult(result) {
  state.fleetResult = result;
}

export function getGlobalFleetResult() {
  return state.fleetResult;
}
