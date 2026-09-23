import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import * as SecureStore from 'expo-secure-store';
import * as TaskManager from 'expo-task-manager';
import { recordLocation } from './api';

export const DRIVER_LOCATION_TASK = 'axiom-fleet-driver-location';
const ACTIVE_DUTY_KEY = 'axiom_driver_active_duty_id';
const LOCATION_BUFFER_KEY = 'axiom_driver_location_buffer_v1';
const MAX_BUFFERED_POINTS = 500;

type BufferedLocation = {
  dutyId: string;
  latitude: number;
  longitude: number;
  recordedAt: string;
  idempotencyKey: string;
  accuracyM?: number;
  batteryPct?: number;
};

let activeFlush: Promise<void> | null = null;

async function readLocationBuffer(): Promise<BufferedLocation[]> {
  try {
    const raw = await AsyncStorage.getItem(LOCATION_BUFFER_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

async function writeLocationBuffer(buffer: BufferedLocation[]): Promise<void> {
  await AsyncStorage.setItem(LOCATION_BUFFER_KEY, JSON.stringify(buffer.slice(-MAX_BUFFERED_POINTS)));
}

function pointFromLocation(dutyId: string, location: Location.LocationObject): BufferedLocation {
  const recordedAt = new Date(location.timestamp).toISOString();
  const latitude = location.coords.latitude;
  const longitude = location.coords.longitude;
  return {
    dutyId,
    latitude,
    longitude,
    recordedAt,
    idempotencyKey: `location-${dutyId}-${location.timestamp}-${latitude.toFixed(6)}-${longitude.toFixed(6)}`,
    accuracyM: location.coords.accuracy ?? undefined,
  };
}

export async function flushLocationBuffer(): Promise<void> {
  if (activeFlush) return activeFlush;
  activeFlush = (async () => {
    let buffer = await readLocationBuffer();
    while (buffer.length) {
      const point = buffer[0];
      try {
        await recordLocation(point.dutyId, point.latitude, point.longitude, point.recordedAt, point.idempotencyKey, point.accuracyM, point.batteryPct);
        buffer = buffer.slice(1);
        await writeLocationBuffer(buffer);
      } catch (_) {
        // Preserve the head of the buffer. The next network transition or task run retries it.
        break;
      }
    }
  })().finally(() => { activeFlush = null; });
  return activeFlush;
}

export async function bufferLocation(dutyId: string, location: Location.LocationObject): Promise<void> {
  const point = pointFromLocation(dutyId, location);
  const buffer = await readLocationBuffer();
  const keys = new Set(buffer.map(item => item.idempotencyKey));
  if (!keys.has(point.idempotencyKey)) await writeLocationBuffer([...buffer, point]);
  await flushLocationBuffer();
}

export async function bufferedLocationCount(): Promise<number> {
  return (await readLocationBuffer()).length;
}

TaskManager.defineTask(DRIVER_LOCATION_TASK, async ({ data, error }) => {
  if (error) return;
  const dutyId = await SecureStore.getItemAsync(ACTIVE_DUTY_KEY);
  const locations = (data as { locations?: Location.LocationObject[] } | undefined)?.locations || [];
  if (!dutyId || !locations.length) return;
  const existing = await readLocationBuffer();
  const keys = new Set(existing.map(item => item.idempotencyKey));
  const additions: BufferedLocation[] = [];
  for (const location of locations) {
    const point = pointFromLocation(dutyId, location);
    if (!keys.has(point.idempotencyKey)) {
      keys.add(point.idempotencyKey);
      additions.push(point);
    }
  }
  if (additions.length) await writeLocationBuffer([...existing, ...additions]);
  await flushLocationBuffer();
});

export async function startBackgroundLocation(dutyId: string): Promise<boolean> {
  const foreground = await Location.requestForegroundPermissionsAsync();
  if (foreground.status !== 'granted') return false;
  const background = await Location.requestBackgroundPermissionsAsync();
  if (background.status !== 'granted') return false;
  await SecureStore.setItemAsync(ACTIVE_DUTY_KEY, dutyId);
  const registered = await TaskManager.isTaskRegisteredAsync(DRIVER_LOCATION_TASK);
  if (!registered) {
    await Location.startLocationUpdatesAsync(DRIVER_LOCATION_TASK, {
      accuracy: Location.Accuracy.Balanced,
      distanceInterval: 100,
      deferredUpdatesInterval: 30000,
      pausesUpdatesAutomatically: false,
      showsBackgroundLocationIndicator: true,
      foregroundService: {
        notificationTitle: 'Axiom Fleet duty active',
        notificationBody: 'Location sharing is on for the active duty.',
        notificationColor: '#0e8b79',
      },
    });
  }
  return true;
}

export async function stopBackgroundLocation(): Promise<void> {
  const registered = await TaskManager.isTaskRegisteredAsync(DRIVER_LOCATION_TASK);
  if (registered) await Location.stopLocationUpdatesAsync(DRIVER_LOCATION_TASK);
  await SecureStore.deleteItemAsync(ACTIVE_DUTY_KEY);
}
