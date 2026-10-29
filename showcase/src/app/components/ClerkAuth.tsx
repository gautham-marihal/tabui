"use client";

import React from "react";
import {
  SignInButton,
  // SignUpButton,
  SignedIn,
  SignedOut,
  SignOutButton,
  useUser,
} from "@clerk/nextjs";

import { clerkConfigured } from "@/lib/auth";

const ClerkSignIn: React.FC = () => {
  const { user } = useUser();

  return (
    <div style={{ textAlign: "center", width: "100%" }}>
      <SignedOut>
        <SignInButton>
          <button>Sign In</button>
        </SignInButton>

        {/* Don't allow Sign-Up from Website. Account provisioning from clerk.com only */}

        {/* <SignUpButton>
          <button>Sign Up</button>
        </SignUpButton> */}
      </SignedOut>

      <SignedIn>
        <div
          style={{
            textAlign: "center",
            width: "100%",
            height: 30,
          }}
        >
          {user?.primaryEmailAddress?.emailAddress}
        </div>
        <SignOutButton>
          <button>Sign Out</button>
        </SignOutButton>
      </SignedIn>
    </div>
  );
};

// what the sign-in page shows when sign-in is not set up (no Clerk key in showcase/.env.local)
const NoSignIn: React.FC = () => (
  <div style={{ textAlign: "center", width: "100%" }}>
    Sign-in is not set up on this site, so every page is open. Add the Clerk keys to showcase/.env.local to turn it on.
  </div>
);

const ClerkAuth = clerkConfigured ? ClerkSignIn : NoSignIn;

export default ClerkAuth;
