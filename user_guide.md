# SattaBase User Guide

> **SattaBase** is the central authentication and billing hub for the **SattaSpace** ecosystem. Sign in once, manage all your subscriptions, and access every connected service from a single dashboard.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
   - [1.1 Creating an Account](#11-creating-an-account)
   - [1.2 Email Verification](#12-email-verification)
   - [1.3 Signing In](#13-signing-in)
   - [1.4 Remember Me](#14-remember-me)
2. [Dashboard](#2-dashboard)
   - [2.1 Overview](#21-overview)
   - [2.2 Getting Started Checklist](#22-getting-started-checklist)
   - [2.3 Quick Actions](#23-quick-actions)
3. [Profile](#3-profile)
   - [3.1 Viewing Your Profile](#31-viewing-your-profile)
   - [3.2 Editing Profile Information](#32-editing-profile-information)
   - [3.3 Avatar Management](#33-avatar-management)
   - [3.4 Email Verification Status](#34-email-verification-status)
4. [Settings](#4-settings)
   - [4.1 Changing Your Password](#41-changing-your-password)
   - [4.2 Changing Your Email Address](#42-changing-your-email-address)
   - [4.3 Signing Out](#43-signing-out)
   - [4.4 Exporting Your Data (GDPR)](#44-exporting-your-data-gdpr)
   - [4.5 Deleting Your Account](#45-deleting-your-account)
5. [Billing & Subscriptions](#5-billing--subscriptions)
   - [5.1 Billing Overview](#51-billing-overview)
   - [5.2 Plans & Pricing](#52-plans--pricing)
   - [5.3 Plan Comparison & Switching](#53-plan-comparison--switching)
   - [5.4 Transaction History](#54-transaction-history)
6. [Account Security](#6-account-security)
   - [6.1 Forgot Password](#61-forgot-password)
   - [6.2 Password Requirements](#62-password-requirements)
   - [6.3 Identity Confirmation](#63-identity-confirmation)
   - [6.4 OTP Security](#64-otp-security)
7. [Navigation & Interface](#7-navigation--interface)
   - [7.1 Sidebar Navigation](#71-sidebar-navigation)
   - [7.2 Top Navigation Bar](#72-top-navigation-bar)
   - [7.3 Dark Mode](#73-dark-mode)
   - [7.4 Mobile Experience](#74-mobile-experience)
8. [Frequently Asked Questions](#8-frequently-asked-questions)

---

## 1. Getting Started

### 1.1 Creating an Account

Visit the registration page and fill in the required information. The registration form includes the following fields:

- **First Name** (required) — Your given name as it will appear across the platform.
- **Last Name** — Your family name (optional but recommended for a complete profile).
- **Email Address** (required) — A valid email address. This serves as your login credential and primary communication channel for account notifications.
- **Password** (required) — Must meet all security requirements (see [Section 6.2](#62-password-requirements)). A real-time strength indicator provides immediate feedback as you type.
- **Confirm Password** (required) — Must match your chosen password exactly.

**Preferences** — Click the gear icon to expand the preferences section. Here you can set your:
- **Timezone** — Auto-detected from your browser, but you can override it.
- **Currency** — Defaults to USD. Choose the currency you prefer to see prices displayed in.
- **Language** — Auto-detected from your browser settings.

After submitting the form, you will be redirected to the email verification page. A 6-digit verification code is sent to your email address.

### 1.2 Email Verification

After registration, you must verify your email address before you can subscribe to paid plans. The verification page presents a set of 6 individual input boxes for your one-time code.

- **Entering the code** — Type each digit and the cursor automatically advances to the next box. You can also paste the entire 6-digit code at once from your clipboard.
- **Navigation** — Use the Backspace key to go back to the previous box. Arrow keys also work for navigation.
- **Resending the code** — If the code expires or you did not receive it, click "Resend code" after a 60-second cooldown period.
- **Code validity** — Verification codes expire after 10 minutes. If your code has expired, simply request a new one.

> **Note:** Email verification is also required for certain security-sensitive operations such as password reset. If you complete a password reset via OTP, your email will be automatically marked as verified.

### 1.3 Signing In

Navigate to the sign-in page and enter your registered email address and password.

- **Email field** — Enter the email address associated with your account.
- **Password field** — Enter your account password. Click the "Forgot password?" link if you need to reset it.
- **Submit** — Click the "Sign in" button or press the Enter key on the password field.

Upon successful authentication, you will be redirected to your dashboard after a brief loading state. If you encounter an error, a message will appear either next to the relevant field or as a general alert at the top of the form, explaining what went wrong.

### 1.4 Remember Me

The "Remember me" checkbox on the sign-in form controls how long your session persists:

| Setting | Behavior |
|---------|----------|
| **Unchecked** (default) | Your session is stored per browser tab. Closing the tab signs you out. Opening a new tab requires you to sign in again. This is the more secure option for shared or public devices. |
| **Checked** | Your session persists across browser tabs, new windows, and browser restarts. You remain signed in until you explicitly sign out or your refresh token expires (7 days). This is convenient for personal devices. |

> **Security Tip:** Only check "Remember me" on trusted, personal devices. On public or shared computers, leave it unchecked.

---

## 2. Dashboard

### 2.1 Overview

The dashboard is your home base after signing in. It provides a personalized summary of your account status and quick access to important areas.

**Greeting** — A time-aware greeting that changes based on the time of day: "Good morning," "Good afternoon," or "Good evening," followed by your first name.

**Email Verification Banner** — If your email is not verified, a prominent yellow banner appears at the top with a "Verify now" button. Email verification is required to subscribe to paid plans.

**Statistics Cards** — Three cards at the top show:
- **Subscription** — Your current plan name, status (e.g., Active, Trialing, Past Due), and days until renewal.
- **Active Plans** — The count of your active subscriptions, with a description of your current plan status.
- **Member Since** — The date you joined SattaBase and your registered email address.

**Recent Billing** — A table showing your 5 most recent transactions including description, invoice number, payment card used, billing period, amount, tax, and status. Each row includes a PDF download link and a hosted invoice link. If you have no transactions yet, a "Browse Plans" link is shown instead.

**Your Subscriptions** — If you have active subscriptions, cards are displayed for each one showing the product name, current plan, status, and relevant dates (trial end, renewal date, etc.). Each card provides links to upgrade, change plans, or manage via the billing portal.

### 2.2 Getting Started Checklist

A progress bar on the dashboard tracks your onboarding progress across four tasks:

1. **Complete your profile** — Fill in your name and profile details. Links to the Profile page.
2. **Verify your email** — Confirm your email address via OTP. Links to the verification page.
3. **Choose a plan** — Subscribe to a paid plan. Links to the Plans & Pricing page.
4. **Set preferences** — Configure your timezone, currency, and language. Links to the Settings or Profile page.

Each item shows a checkmark when completed and remains clickable (linking to the relevant page) when pending. The overall progress percentage is displayed at the top of the checklist.

### 2.3 Quick Actions

Four quick-action cards provide one-click shortcuts to the most commonly used areas:

- **Manage Billing** — Opens the Stripe billing portal (only shown if you have an active paid subscription).
- **View Plans** — Navigates to the Plans & Pricing page to browse available options.
- **Profile** — Goes to your profile page to view or edit personal information.
- **Settings** — Opens account settings for security and preference management.

---

## 3. Profile

### 3.1 Viewing Your Profile

The profile page displays your personal information in a two-column layout. On the left, your avatar and key identity information are shown. On the right, all editable fields are presented in a clean grid.

**Left Column (Identity Card):**
- **Avatar** — Your profile picture, or a circle with your initials if no image is uploaded.
- **Name & Email** — Your full name and registered email address.
- **Verification Badge** — A green "Verified" badge if your email is confirmed, or a yellow "Unverified" badge if it is not.
- **Role** — Your account role displayed as a muted pill badge.
- **Member Since** — The date your account was created.

### 3.2 Editing Profile Information

Click the "Edit profile" button on the right column to switch to edit mode. The following fields become editable:

| Field | Description |
|-------|-------------|
| First Name | Your given name. |
| Last Name | Your family name. |
| Phone | Optional phone number for account communication. |
| Timezone | Select from a searchable dropdown of all IANA timezones (e.g., Asia/Dhaka, America/New_York). The list is searchable — start typing to filter results. |
| Currency | Select your preferred display currency from a searchable list. Prices across the platform will be shown in this currency where supported. |
| Language | Select your preferred interface language from a searchable dropdown. |

All dropdown fields feature full-text search. Type a city name, country, or timezone code to quickly find the right option. Click "Save changes" to apply your edits or "Cancel" to discard them.

### 3.3 Avatar Management

Your profile picture helps personalize your account and appears across the SattaBase interface (sidebar, navbar dropdown, profile page).

**Uploading an avatar:**
1. Click the camera icon button on your avatar (visible when hovering on the profile page).
2. Select an image from your device.
3. Accepted formats: **JPEG, PNG, GIF, and WebP**.
4. Maximum file size: **2 MB**.
5. The image is uploaded immediately and displayed.

**Removing your avatar:**
- Click the red X button that appears in the top-right corner of your avatar.
- This removes the image and reverts to the initials-based fallback.

### 3.4 Email Verification Status

Your verification status is prominently displayed on the profile page. If your email is unverified:
- A yellow warning section appears with a "Verify email now" button.
- A "Resend verification email" link is available with a 60-second cooldown between sends.
- After verifying, the badge turns green and the warning section disappears.

---

## 4. Settings

The settings page contains all account security and management options organized into separate card sections.

### 4.1 Changing Your Password

The "Change Password" card allows you to update your password at any time while signed in.

1. **Current Password** — Enter your existing password for verification.
2. **New Password** — Enter your new password. The same real-time strength indicator from registration is shown here, ensuring your new password meets all requirements.
3. **Confirm New Password** — Re-enter the new password to confirm it matches.
4. Click "Change password" to apply the change.

If the current password is incorrect, an error message is displayed and no changes are made.

> **Important:** Changing your password does not sign you out. You will remain logged in with your new credentials. If you believe your account has been compromised, change your password and then sign out from all devices.

### 4.2 Changing Your Email Address

The email change process is a 3-step flow designed to ensure security:

**Step 1 — Initiate the change:**
- Enter your current password (unless you have already verified your identity within the last 5 minutes via the Identity Confirmation gate).
- Enter the new email address you want to switch to.
- Click "Send verification code."

**Step 2 — Verify via OTP:**
- A 6-digit code is sent to your **current** email address (not the new one). This confirms that you — the account owner — are authorizing the change.
- Enter the code using the 6-digit OTP input boxes.
- An info banner confirms: "A verification code has been sent to your current email. You are changing to [new email]."
- If you do not receive the code, use the "Resend code" link after the 60-second cooldown.
- Click "Confirm email change" to proceed.

**Step 3 — Confirmation:**
- A green checkmark confirms the email has been updated.
- You are automatically signed out after 2 seconds.
- Sign in with your new email address going forward.

> **Note:** If the identity confirmation gate (see [Section 6.3](#63-identity-confirmation)) has been unlocked within the last 5 minutes, the password field in Step 1 is skipped and a green "Verified" badge is shown instead.

### 4.3 Signing Out

Click the "Sign out" button in the settings page. A confirmation dialog appears asking "Are you sure you want to sign out?" with two options:

- **Yes, sign out** — Clears your session and redirects to the sign-in page.
- **Cancel** — Returns to the settings page without signing out.

You can also sign out from the user dropdown menu in the top navigation bar, or from the sign-out button at the bottom of the sidebar.

### 4.4 Exporting Your Data (GDPR)

SattaBase provides a data export feature in compliance with GDPR Article 20 (Right to Data Portability).

- Click the "Export billing data" button on the settings page.
- A JSON file named `sattabase_billing_export_{your-email}_{date}.json` is downloaded to your device.
- The file contains all of your billing data including transactions, subscriptions, invoices, and account details.

> **Note:** This export covers billing-related data. The export is generated on-demand and contains a snapshot of your data at the time of download.

### 4.5 Deleting Your Account

Account deletion is a permanent action that cannot be undone. The process includes multiple safeguards:

**Identity Confirmation Gate:**
Before you can access the delete account option, you must verify your identity:
1. A warning box explains: "Enter your password to unlock sensitive actions. Lasts 5 minutes."
2. Enter your current password and click "Verify."
3. A countdown timer shows the remaining time until re-verification is required (5 minutes).
4. Click "Clear" to manually lock the gate again if needed.

**Account Deletion Flow:**
Once identity is confirmed, the delete account section becomes available:
1. Click "Permanently delete my account."
2. A modal dialog appears with:
   - A clear warning that the action is permanent and all data will be lost.
   - A password field (pre-filled if you just verified your identity).
   - A text input requiring you to type exactly **"DELETE MY ACCOUNT"** to proceed.
3. Click "Permanently delete my account" (red/destructive button) to confirm.
4. Click "Cancel" at any point to abort.

> **Warning:** Deleting your account permanently removes all your data, including subscriptions, billing history, profile information, and uploaded avatars. This action cannot be reversed.

---

## 5. Billing & Subscriptions

### 5.1 Billing Overview

The billing overview page is your central hub for managing all subscriptions within the SattaSpace ecosystem.

**Alert Banners:**
- **Past-due (red)** — If a payment has failed, a red banner appears with an "Update Payment Method" button directing you to the Stripe billing portal.
- **Paused (gray)** — If a subscription is paused, a gray banner appears with a "Manage in Portal" button.

**Statistics Cards:** Four cards summarize your billing status:
- **Active Plans** — Number of currently active subscriptions.
- **Products** — Number of distinct products you are subscribed to.
- **Next Billing Date** — When your next payment is due.
- **Paid Plans** — Number of subscriptions on paid tiers.

**Subscription Cards:** Each subscription is displayed as an expandable card showing:
- Product name with initial-based avatar.
- Current plan name and status badge (Active, Trialing, Past Due, Canceled, Paused).
- Trial end date, renewal date, or cancellation date as applicable.
- **Action buttons:**
  - **Details** — Expands the card to show plan features, usage limits, metadata, and billing history.
  - **Upgrade** — Navigate to plan comparison for the product.
  - **View Plans** — Go to the plans landing page.
  - **Manage** — Open the Stripe billing portal for payment method updates and invoice management.
  - **Cancel** — Opens a cancellation dialog (see below).
  - **Reactivate** — Resume a canceled subscription before the end of the billing period.
  - **Fix Payment** — Resolve a failed payment by updating your payment method via Stripe.

**Canceling a Subscription:**
When you click "Cancel" on a subscription card, a modal dialog appears:
- A reason textarea lets you optionally explain why you are canceling (this feedback helps improve the service).
- "Cancel Subscription" confirms the cancellation.
- "Go Back" returns without changes.
- The modal supports keyboard navigation: Escape to close, focus trap for accessibility.

**Stripe Checkout Integration:**
If you return from a Stripe checkout session (successful payment), SattaBase automatically detects this and refreshes your subscription data. Similarly, returning from the Stripe billing portal triggers a data sync.

### 5.2 Plans & Pricing

The plans landing page displays all available products and their plan tiers in an organized card layout.

**Product Cards:**
Each product is represented by a card showing:
- Product name, description, and initial-based avatar.
- **Service domains** — Monospace badges showing the domains associated with each product (e.g., `app.example.com`), with a "primary" tag on the main domain.
- **Current subscription status** — If you are already subscribed to this product, a badge shows your active plan (e.g., "Active — Pro Plan").
- **Plan summary grid** — A responsive grid of cards (up to 3 columns), each showing:
  - Plan name.
  - Price and billing cycle (monthly/yearly).
  - Number of features included.
  - Trial days available (e.g., "14-day free trial").
  - "Current" badge on your active plan.
  - "Popular" badge on the featured/recommended plan.
- A "Compare plans & manage subscription" button that links to the detailed plan comparison page for that product.

### 5.3 Plan Comparison & Switching

The plan comparison page for a specific product provides a detailed side-by-side view of all available plans with full feature lists and switching options.

**Page Header:**
- Product name and description.
- Service domains listed as badges.
- If you have an active subscription, your current plan is shown with its status and relevant dates.

**Feature Comparison:**
Each plan card displays its full feature list with semantic icons:
- **Blue hash icon** — Numeric limits (e.g., "10 projects").
- **Purple infinity icon** — Unlimited features.
- **Green checkmark** — Included boolean features.

**Pricing Details:**
- Price is shown in your preferred currency (configured in profile settings).
- If your currency differs from USD, a conversion disclaimer is displayed noting that charges are processed in USD.
- **Annual savings badge** — For annual plans, the savings percentage vs. monthly billing is shown (e.g., "Save 17% vs monthly").
- **Trial badge** — If a free trial is available, the trial duration is highlighted.

**Switching Plans:**
The action button on each plan card changes based on your current plan and subscription status:

| Your Status | Free Plan | Paid Plan (Higher) | Paid Plan (Lower) | Same Plan |
|-------------|-----------|--------------------|--------------------|-----------|
| No subscription | "Subscribe" | "Subscribe" with trial info | N/A | N/A |
| Free plan | "Current Plan" (disabled) | "Upgrade Now" | N/A | N/A |
| Paid plan | "Downgrade to Free" | "Upgrade Now" | "Downgrade" | "Current Plan" (disabled) |
| Canceled (within period) | N/A | "Reactivate Plan" | N/A | N/A |

**Proration Modal:**
When switching between paid plans, a proration modal appears before confirming:
- Shows the title: "Upgrade," "Downgrade," or "Switch Plan."
- **Amount due now** (for upgrades) — The prorated charge for the remaining billing period.
- **Prorated credit** (for downgrades) — The credit applied to your next invoice.
- Tax calculation and next billing amount.
- **Upgrade behavior** — Your card is charged immediately for the prorated difference.
- **Downgrade behavior** — The change takes effect at the start of your next billing cycle.
- Cancel or confirm with "Pay & Upgrade" / "Confirm Change."

A Terms of Service checkbox must be checked before any paid plan selection can proceed.

### 5.4 Transaction History

The transaction history page provides a complete record of all billing events.

**Summary Statistics:** Four cards at the top show:
- **Total Spent** — Cumulative amount across all paid transactions.
- **Total Tax** — Cumulative tax paid.
- **Pending** — Count of transactions awaiting payment.
- **Invoices** — Total count of invoices, including a count of any failed payment attempts.

**Filter Tabs:**
- **All** — Shows every transaction.
- **Paid** — Successfully completed transactions only.
- **Pending** — Transactions awaiting payment processing.
- **Failed** — Transactions that did not complete, including the number of payment attempts made.

Each filter tab displays a count badge showing the number of transactions in that category.

**Transaction Table:**
Each transaction row displays:
- **Description** — What the transaction was for (e.g., plan subscription, renewal).
- **Invoice Number** — Unique invoice identifier.
- **Payment Method** — Card brand and last 4 digits (e.g., "Visa ending in 4242").
- **Billing Period** — The time range covered by the transaction.
- **Status** — Color-coded badge: green (Paid), amber (Pending), red (Failed). Failed transactions also show the number of payment attempts.
- **Amount** — Total charged, with a tax breakdown.
- **Date** — When the transaction was processed.
- **Actions** — PDF download button and a link to the hosted invoice.

**Pagination:**
Transactions are loaded 25 at a time. Click "Load More Transactions" at the bottom to load the next batch. When all transactions have been loaded, an indicator shows "Showing all N transactions."

**Empty States:**
- If you have no transactions at all, a friendly message appears with a "Browse Plans" link.
- If a specific filter returns no results, a message indicates that no transactions match the current filter.

---

## 6. Account Security

### 6.1 Forgot Password

If you forget your password, you can reset it securely using a 2-step OTP (one-time password) process. Navigate to `/auth/forgot-password` or click "Forgot password?" on the sign-in page.

**Step 1 — Verify your email:**
1. Enter the email address associated with your account.
2. Click "Send verification code."
3. A 6-digit code is sent to your email address.
4. The form advances to Step 2 regardless of whether the email exists in the system (this prevents email enumeration attacks).

**Step 2 — Verify and reset:**
1. Your target email is displayed in bold — confirm it is correct.
2. Enter the 6-digit code using the OTP input boxes.
3. Enter and confirm your new password (the same strength indicator applies).
4. Click "Reset password."
5. On success, a green confirmation screen appears with a "Sign in" button.

**Additional options:**
- **Resend code** — Available after a 60-second cooldown. A timer counts down the remaining time.
- **Different email** — Click "Use a different email" to go back to Step 1.
- **Remember your password?** — A sign-in link is available throughout the flow.

> **Important:** Successfully resetting your password via OTP automatically marks your email as verified if it was not already. Completing an OTP verification proves email ownership.

**Security Tips:**
- Verification codes expire after 10 minutes. Request a new one if yours has expired.
- You have a maximum of 5 attempts to enter the correct code. After that, you must request a new code.
- Check your spam or junk folder if you do not see the email within a minute.

### 6.2 Password Requirements

All password fields across SattaBase (registration, password change, password reset) enforce the following requirements:

| Requirement | Description |
|-------------|-------------|
| Minimum length | At least **8 characters** |
| Uppercase | At least one **uppercase letter** (A-Z) |
| Lowercase | At least one **lowercase letter** (a-z) |
| Number | At least one **digit** (0-9) |
| Special character | At least one **special character** (e.g., !@#$%^&*) |

A real-time strength indicator provides visual feedback:
- **Weak** (red) — Fails most requirements.
- **Fair** (yellow) — Meets some requirements.
- **Good** (light green) — Meets most requirements.
- **Strong** (green/brand) — Meets all requirements.

A checklist below the strength bar shows individual checkmarks for each requirement, turning green as each one is satisfied.

### 6.3 Identity Confirmation

Certain sensitive operations in the Settings page require you to re-confirm your identity before proceeding. This adds an extra layer of security beyond your active session.

**How it works:**
1. An amber warning box prompts you to "Enter your password to unlock sensitive actions."
2. Enter your current password and click "Verify."
3. Upon successful verification, a green badge appears showing the verification time and a countdown timer.
4. The identity confirmation remains valid for **5 minutes**, during which sensitive actions (like account deletion) can proceed without re-entering your password.
5. Click "Clear" to manually revoke the confirmation at any time.
6. Rate limit: A maximum of **10 verification attempts per hour** to prevent brute-force attacks.

### 6.4 OTP Security

SattaBase uses one-time passwords (OTP) for several critical operations. Here is how OTP security is maintained:

**Where OTP is used:**
- Email verification after registration.
- Password reset.
- Email address change (verification sent to current email).

**Security measures:**
- Each OTP is a randomly generated 6-digit code (cryptographically secure).
- Codes expire after **10 minutes**.
- A maximum of **5 incorrect attempts** are allowed per code, after which the code is invalidated and a new one must be requested.
- Resend cooldown of **60 seconds** between code requests prevents spamming.
- OTPs are stored server-side in a cache with automatic expiration and are never stored in the database.

**Input security:**
- OTP input boxes auto-advance after each digit is entered.
- Full paste support — paste the entire code and it fills all boxes.
- Backspace and arrow key navigation for easy correction.
- No autocomplete or autofill on OTP fields to prevent credential manager interference.

---

## 7. Navigation & Interface

### 7.1 Sidebar Navigation

The sidebar is the primary navigation element on desktop (visible on screens 1024px and wider). It provides organized access to all sections of SattaBase.

**Brand Identity:**
- At the top, the SattaBase logo and name are displayed alongside a gradient accent line.

**Navigation Sections:**
Two collapsible sections organize the navigation items:

| Section | Items |
|---------|-------|
| **General** | Dashboard, Profile, Settings |
| **Billing** | Overview, Plans, Transactions |

Each section can be collapsed or expanded by clicking the section header. The chevron icon rotates to indicate the current state.

**Active State:**
- The currently active page is highlighted with a brand-colored background.
- A vertical indicator bar appears on the left edge of the active item.
- The active item's icon is slightly brighter.

**Keyboard Navigation:**
- Use **Up/Down arrow keys** to move between navigation items.
- Press **Home** to jump to the first item, **End** to jump to the last.
- Press **Enter** or **Space** to navigate to the selected item.

**Bottom Section:**
- **Subscription status bar** — Shows a colored dot indicating your overall subscription status (green = active, blue = trialing, amber = past due, gray = free) alongside your current plan name. A "Manage" link goes to the billing overview.
- **User info card** — Displays your avatar initials, name, and email. Clicking navigates to your profile.
- **Sign out** — A sign-out button at the very bottom. It turns red on hover to indicate the destructive nature of the action.

### 7.2 Top Navigation Bar

The top navigation bar (navbar) provides quick access to features and user-specific actions.

**Left Side:**
- **Mobile** — Hamburger menu button to open the sidebar overlay. SattaBase logo and name.
- **Desktop** — Breadcrumb navigation showing "Dashboard" as the base link.

**Right Side:**
- **Dark mode toggle** — Click the sun/moon icon to switch between light and dark themes.
- **Notifications bell** — Displays a badge with the notification count. Currently shows "No notifications yet" when expanded.
- **User dropdown** — Click your avatar/name to expand a dropdown with:
  - Your name, email, and currency badge.
  - Links to Profile and Settings.
  - Sign out button.

All dropdowns close when clicking outside of them or pressing the Escape key.

### 7.3 Dark Mode

SattaBase supports both light and dark themes. Toggle between them using the moon/sun icon in the top navigation bar.

- Your preference is saved to your browser's local storage.
- On your first visit, the system respects your operating system's preference (via `prefers-color-scheme` media query).
- The theme applies immediately without page reload.

### 7.4 Mobile Experience

On mobile devices (screens narrower than 1024px), the interface adapts for touch-friendly navigation:

**Sidebar becomes an overlay:**
- Tap the hamburger menu icon in the top-left corner to open the sidebar as a slide-in panel.
- The panel slides in from the left with a dark backdrop overlay.
- Swipe left on the panel to dismiss it (swipe threshold: 30% of panel width).
- Tap the X button or the backdrop to close the sidebar.
- The sidebar automatically closes when the screen is resized past the desktop breakpoint.

**Layout adjustments:**
- The sidebar is hidden by default and replaced by the hamburger menu.
- Content areas use full width.
- Transaction tables switch from a grid layout to stacked card view for easier reading on narrow screens.
- Navigation sections and action buttons are touch-optimized with adequate tap targets.

---

## 8. Frequently Asked Questions

**Q: Do I need to verify my email to use SattaBase?**
A: You can sign in and explore the dashboard without verifying your email. However, email verification is required to subscribe to any paid plans. You will see a reminder banner on the dashboard until your email is verified.

**Q: I registered but cannot find the verification email. What should I do?**
A: First, check your spam or junk folder. If it is not there, go to the verification page and click "Resend code" (available after a 60-second cooldown). Make sure you are checking the correct email inbox. If you still do not receive it, verify that you entered the correct email during registration.

**Q: How do I reset my password?**
A: Click "Forgot password?" on the sign-in page, or navigate directly to `/auth/forgot-password`. Enter your email, then follow the OTP-based reset process (see [Section 6.1](#61-forgot-password)). Successfully resetting your password also verifies your email if it was not already verified.

**Q: What happens to my data if I cancel a subscription?**
A: Canceling a subscription stops future billing charges. You retain access to the paid plan features until the end of your current billing period. After that, your subscription reverts to the free tier (if available) or is deactivated. Your historical data, including past transactions and invoices, remains accessible.

**Q: Can I switch between monthly and annual billing?**
A: Yes. Go to the plan comparison page for your product and select the plan with your preferred billing cycle. A proration modal will show you the cost adjustment before confirming the change.

**Q: Is my payment information stored on SattaBase?**
A: No. SattaBase does not store credit card numbers or payment details. All payment processing is handled by **Stripe**, a PCI-DSS compliant payment processor. SattaBase only stores a reference to your Stripe customer and subscription IDs.

**Q: What is the identity confirmation gate in Settings?**
A: It is an additional security layer for sensitive operations like account deletion. You must enter your password to unlock the gate, which remains valid for 5 minutes. This prevents unauthorized changes if someone gains access to your active session.

**Q: How do I export all my data?**
A: Go to Settings and click "Export billing data" in the GDPR section. A JSON file containing all your billing data will be downloaded immediately. This is available at any time without requiring identity confirmation.

**Q: Can I change my email address?**
A: Yes. Go to Settings and use the "Change Email" section. A verification code is sent to your current email address for security. After confirming, you are signed out and must sign in with the new email.

**Q: What does "Remember me" do on the sign-in page?**
A: When unchecked (default), your session is per browser tab — closing the tab signs you out. When checked, your session persists across tabs, new windows, and browser restarts for up to 7 days (refresh token lifetime). Use it only on trusted personal devices.

**Q: How do I delete my account?**
A: Go to Settings, verify your identity via the confirmation gate, then follow the account deletion flow. You must type "DELETE MY ACCOUNT" to confirm. This action is permanent and cannot be undone — all data including subscriptions, transactions, and profile information will be removed.

---

*This guide reflects the current feature set of SattaBase. Features and interfaces may be updated as the platform evolves.*
