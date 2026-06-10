// Realtime Offline-first Sync Adapter routing through Express and JSON Flat File Database on the Server

// === Timestamp Helper Class ===
export class Timestamp {
  seconds: number;
  nanoseconds: number;

  constructor(seconds: number, nanoseconds: number) {
    this.seconds = seconds;
    this.nanoseconds = nanoseconds;
  }

  static now() {
    return Timestamp.fromMillis(Date.now());
  }

  static fromDate(date: Date) {
    return Timestamp.fromMillis(date.getTime());
  }

  static fromMillis(ms: number) {
    const seconds = Math.floor(ms / 1000);
    const nanoseconds = (ms % 1000) * 1000000;
    return new Timestamp(seconds, nanoseconds);
  }

  toDate() {
    return new Date(this.toMillis());
  }

  toMillis() {
    return this.seconds * 1000 + Math.floor(this.nanoseconds / 1000000);
  }
}

const serverTimestampToken = { _isServerTimestamp: true };

export function serverTimestamp() {
  return serverTimestampToken;
}

// === Database Serialization Helpers ===
function restoreTimestamps(val: any): any {
  if (val === null || val === undefined) return val;
  if (typeof val === 'object') {
    if (val._isTimestamp === true || (typeof val.seconds === 'number' && typeof val.nanoseconds === 'number')) {
      return new Timestamp(val.seconds, val.nanoseconds);
    }
    if (Array.isArray(val)) {
      return val.map(restoreTimestamps);
    }
    const res: any = {};
    for (const k of Object.keys(val)) {
      res[k] = restoreTimestamps(val[k]);
    }
    return res;
  }
  return val;
}

function serializeTimestamps(val: any): any {
  if (val === null || val === undefined) return val;
  if (val instanceof Timestamp) {
    return { _isTimestamp: true, seconds: val.seconds, nanoseconds: val.nanoseconds };
  }
  if (val instanceof Date) {
    return serializeTimestamps(Timestamp.fromDate(val));
  }
  if (typeof val === 'object') {
    if (Array.isArray(val)) {
      return val.map(serializeTimestamps);
    }
    const res: any = {};
    for (const k of Object.keys(val)) {
      res[k] = serializeTimestamps(val[k]);
    }
    return res;
  }
  return val;
}

function processServerTimestamps(val: any): any {
  if (val === serverTimestampToken) {
    return Timestamp.now();
  }
  if (val === null || val === undefined) return val;
  if (typeof val === 'object') {
    if (Array.isArray(val)) {
      return val.map(processServerTimestamps);
    }
    const res: any = {};
    for (const k of Object.keys(val)) {
      res[k] = processServerTimestamps(val[k]);
    }
    return res;
  }
  return val;
}

// === Event Listener Registry (Realtime Streams) ===
type ListenerCallback = () => void;
const realtimeListeners = new Set<ListenerCallback>();

function notifyListeners() {
  realtimeListeners.forEach(listener => {
    try {
      listener();
    } catch (e) {
      console.error("Error in onSnapshot update trigger:", e);
    }
  });
}

// === Mock Firestore SDK ===
interface DocRef {
  type: 'doc';
  path: string;
  id: string;
}

interface CollectionRef {
  type: 'collection';
  path: string;
  id: string;
}

interface QueryRef {
  type: 'collection';
  path: string;
  constraints: any[];
}

export function collection(dbRef: any, ...segments: string[]): CollectionRef {
  let pathSegments = segments.filter(Boolean);
  if (dbRef && typeof dbRef === 'object' && dbRef.type) {
    pathSegments = [dbRef.path, ...pathSegments];
  }
  const path = pathSegments.join('/');
  return {
    type: 'collection',
    path,
    id: pathSegments[pathSegments.length - 1] || ''
  };
}

export function doc(dbRef: any, ...segments: string[]): DocRef {
  let pathSegments = segments.filter(Boolean);
  if (dbRef && typeof dbRef === 'object' && dbRef.type) {
    pathSegments = [dbRef.path, ...pathSegments];
  }
  const path = pathSegments.join('/');
  return {
    type: 'doc',
    path,
    id: pathSegments[pathSegments.length - 1] || ''
  };
}

export function query(collectionRef: any, ...constraints: any[]): QueryRef {
  return {
    type: 'collection',
    path: collectionRef.path,
    constraints: constraints.filter(Boolean)
  };
}

export function where(field: string, op: string, value: any) {
  return { type: 'where', field, op, value };
}

export function orderBy(field: string, direction: 'asc' | 'desc' = 'asc') {
  return { type: 'orderBy', field, direction };
}

export function onSnapshot(ref: any, onNext: (snap: any) => void, onError?: (err: any) => void) {
  let active = true;
  let lastHash = '';

  const runSubscription = async () => {
    if (!active) return;
    try {
      if (ref.type === 'doc') {
        const response = await fetch(`/api/db/get?path=${encodeURIComponent(ref.path)}`);
        if (!response.ok) throw new Error(await response.text());
        const res = await response.json();
        
        const currentHash = JSON.stringify(res);
        if (currentHash !== lastHash) {
          lastHash = currentHash;
          onNext({
            id: ref.id,
            exists: () => res.exists,
            data: () => res.data ? restoreTimestamps(res.data) : null
          });
        }
      } else {
        const path = ref.path;
        const constraints = ref.constraints || [];
        const response = await fetch('/api/db/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path, constraints })
        });
        if (!response.ok) throw new Error(await response.text());
        const res = await response.json();
        
        const currentHash = JSON.stringify(res);
        if (currentHash !== lastHash) {
          lastHash = currentHash;
          const docs = (res.docs || []).map((docData: any) => {
            const id = docData.id || docData.uid;
            return {
              id,
              data: () => restoreTimestamps(docData)
            };
          });
          onNext({
            docs,
            length: docs.length
          });
        }
      }
    } catch (err: any) {
      console.error("Polled subscription fetch failed: ", err);
      if (onError) onError(err);
    } finally {
      // Schedule next polling heartbeat cycle in 1000ms
      if (active) {
        setTimeout(runSubscription, 1000);
      }
    }
  };

  // Register internal notifier for immediate updates upon writes
  const immediateTrigger = () => {
    runSubscription();
  };
  realtimeListeners.add(immediateTrigger);

  // Run first fetch immediately
  runSubscription();

  return () => {
    active = false;
    realtimeListeners.delete(immediateTrigger);
  };
}

export async function addDoc(collectionRef: any, data: any) {
  const processed = serializeTimestamps(processServerTimestamps(data));
  const response = await fetch('/api/db/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: collectionRef.path, data: processed })
  });
  
  if (!response.ok) {
    throw new Error(`Write failed on server: ${await response.text()}`);
  }

  const res = await response.json();
  notifyListeners();
  
  return {
    id: res.id,
    path: `${collectionRef.path}/${res.id}`
  };
}

export async function setDoc(docRef: any, data: any, options?: { merge?: boolean }) {
  const processed = serializeTimestamps(processServerTimestamps(data));
  const response = await fetch('/api/db/set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: docRef.path, data: processed, options })
  });

  if (!response.ok) {
    throw new Error(`Write failed on server: ${await response.text()}`);
  }

  notifyListeners();
}

export async function updateDoc(docRef: any, data: any) {
  const processed = serializeTimestamps(processServerTimestamps(data));
  const response = await fetch('/api/db/set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: docRef.path, data: processed, options: { merge: true } })
  });

  if (!response.ok) {
    throw new Error(`Update failed on server: ${await response.text()}`);
  }

  notifyListeners();
}

export async function deleteDoc(docRef: any) {
  const response = await fetch('/api/db/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: docRef.path })
  });

  if (!response.ok) {
    throw new Error(`Delete failed on server: ${await response.text()}`);
  }

  notifyListeners();
}

export async function getDoc(docRef: any) {
  const response = await fetch(`/api/db/get?path=${encodeURIComponent(docRef.path)}`);
  if (!response.ok) {
    throw new Error(`Get failed on server: ${await response.text()}`);
  }
  const res = await response.json();
  return {
    id: docRef.id,
    exists: () => res.exists,
    data: () => res.data ? restoreTimestamps(res.data) : null
  };
}

export async function getDocs(queryOrColRef: any) {
  const path = queryOrColRef.path;
  const constraints = queryOrColRef.constraints || [];
  const response = await fetch('/api/db/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, constraints })
  });

  if (!response.ok) {
    throw new Error(`Query failed on server: ${await response.text()}`);
  }

  const res = await response.json();
  const docs = (res.docs || []).map((docData: any) => {
    const id = docData.id || docData.uid;
    return {
      id,
      data: () => restoreTimestamps(docData)
    };
  });

  return {
    docs,
    length: docs.length
  };
}

// === Mock Auth SDK ===
class MockAuth {
  currentUser: any = null;
  constructor() {
    this.currentUser = {
      uid: "snt82gjjo5QrMdbyiEakOZW6JD33",
      displayName: "Kabita Gorain",
      email: "kabitagorain6@gmail.com",
      photoURL: "https://avatar.iran.liara.run/public/60",
      emailVerified: true,
      isAnonymous: false,
      providerData: [
        { providerId: 'google.com', email: "kabitagorain6@gmail.com" }
      ]
    };
  }
}

export const authInstance = new MockAuth();

export function getAuth() {
  return authInstance;
}

export class GoogleAuthProvider {
  constructor() {}
}

export async function signInWithPopup(authObj: any, provider: any) {
  const mockUser = {
    uid: "snt82gjjo5QrMdbyiEakOZW6JD33",
    displayName: "Kabita Gorain",
    email: "kabitagorain6@gmail.com",
    photoURL: "https://avatar.iran.liara.run/public/60",
    emailVerified: true,
    isAnonymous: false,
    providerData: [
      { providerId: 'google.com', email: "kabitagorain6@gmail.com" }
    ]
  };
  authObj.currentUser = mockUser;
  notifyAuthListeners();
  return { user: mockUser };
}

export async function signOut(authObj: any) {
  authObj.currentUser = null;
  notifyAuthListeners();
}

export async function signInAnonymously(authObj: any) {
  const mockUser = {
    uid: "snt82gjjo5QrMdbyiEakOZW6JD33",
    displayName: "Kabita Gorain",
    email: "kabitagorain6@gmail.com",
    photoURL: "https://avatar.iran.liara.run/public/60",
    emailVerified: true,
    isAnonymous: false,
    providerData: [
      { providerId: 'google.com', email: "kabitagorain6@gmail.com" }
    ]
  };
  authObj.currentUser = mockUser;
  notifyAuthListeners();
  return { user: mockUser };
}

const authListeners = new Set<(user: any) => void>();

function notifyAuthListeners() {
  authListeners.forEach(listener => {
    try {
      listener(authInstance.currentUser);
    } catch (e) {
      console.error(e);
    }
  });
}

export function onAuthStateChanged(authObj: any, callback: (user: any) => void) {
  authListeners.add(callback);
  setTimeout(() => {
    callback(authInstance.currentUser);
  }, 0);
  
  return () => {
    authListeners.delete(callback);
  };
}

// === Mock App SDK ===
export function initializeApp() {
  return { name: '[MockApp]' };
}

export function getFirestore(app: any, databaseId?: string) {
  return { type: 'db', app, databaseId };
}

// Export pre-initialized objects to support direct file usages
export const db = getFirestore(null);
export const auth = authInstance;
export const googleProvider = new GoogleAuthProvider();
export const signIn = () => signInWithPopup(authInstance, googleProvider);
export const logOut = () => signOut(authInstance);
