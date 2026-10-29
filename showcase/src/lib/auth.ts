"use client";

import { useUser } from "@clerk/nextjs";

import { clerkConfigured } from "./clerkSetting";

// Sign-in (Clerk) is on only when its key is set in showcase/.env.local. Without it the site runs and builds with no
// sign-in at all: nothing can be protected then (the middleware lets every page through), so nothing is hidden either.
export { clerkConfigured };

type SignedIn = { isSignedIn: boolean; email: string };

function useClerkSignedIn(): SignedIn {
  const { isSignedIn, user } = useUser();
  return { isSignedIn: Boolean(isSignedIn), email: user?.primaryEmailAddress?.emailAddress || "" };
}

function useNoSignIn(): SignedIn {
  return { isSignedIn: false, email: "" };
}

/** Whether someone is signed in, and as whom; always "no" when sign-in is not set up. Chosen once, when the site is built. */
export const useSignedIn = clerkConfigured ? useClerkSignedIn : useNoSignIn;
