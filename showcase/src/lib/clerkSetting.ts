// Whether sign-in (Clerk) is set up: its key is in showcase/.env.local. Read by the server (the layout) and the browser
// (lib/auth.ts) alike, so it lives apart from the client-only hooks: a server component importing a value from a
// "use client" file gets a stand-in, not the value.
export const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
