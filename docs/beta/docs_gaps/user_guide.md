# CareerVP User Guide

**Version:** 1.0 (Beta)
**Last Updated:** 2026-02-25

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Managing Your CV](#2-managing-your-cv)
3. [Job Applications](#3-job-applications)
4. [Gap Analysis](#4-gap-analysis)
5. [Generating VPR](#5-generating-vpr)
6. [CV Tailoring](#7-cv-tailoring)
7. [Cover Letters](#8-cover-letters)
8. [Interview Preparation](#9-interview-preparation)
9. [Trial & Billing](#10-trial--billing)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Getting Started

### 1.1 Registration

1. Visit the CareerVP signup page
2. Enter your email address
3. Create a password (minimum 8 characters)
4. Enter your full name
5. Click "Create Account"

### 1.2 Login

1. Visit the CareerVP login page
2. Enter your email and password
3. Click "Login"
4. You'll be redirected to your dashboard

### 1.3 Dashboard Overview

After logging in, you'll see your dashboard with:
- **Quick Actions**: Start new tasks
- **Recent Activity**: Your latest applications
- **Trial Status**: Days remaining and applications used

---

## 2. Managing Your CV

### 2.1 Uploading a CV

1. Navigate to **CVs** in the sidebar
2. Click **Upload CV**
3. Select your CV file (PDF, DOCX, or TXT)
4. Enter a name for your CV (e.g., "Software Engineer CV")
5. Click **Upload**

**Supported formats:** PDF, DOCX, TXT
**Maximum size:** 10MB

### 2.2 Viewing Your CVs

1. Go to **CVs**
2. You'll see a list of all uploaded CVs
3. Click on a CV to view details
4. You can delete CVs you no longer need

### 2.3 Selecting a Primary CV

For each job application, you can select which CV to use:

1. When creating a job application
2. Select from your uploaded CVs
3. Or upload a new CV for this application

---

## 3. Job Applications

### 3.1 Creating a Job Application

1. Go to **Jobs** in the sidebar
2. Click **New Application**
3. Enter the job details:
   - **Company Name** (required)
   - **Job Title** (required)
   - **Job Description** (paste or upload)
   - **Job Post URL** (optional)
   - **Location** (optional)
4. Select your CV to use
5. Click **Create Application**

### 3.2 Viewing Applications

1. Go to **Jobs**
2. You'll see all your applications listed
3. Each shows: Company, Title, Status, Date
4. Click an application to see details

### 3.3 Application Statuses

| Status | Meaning |
|--------|---------|
| Draft | Application not yet submitted |
| In Progress | Currently being worked on |
| Complete | All documents generated |
| Expired | Trial period ended |

---

## 4. Gap Analysis

### 4.1 What is Gap Analysis?

Gap Analysis compares your skills to the job requirements and identifies areas where your background matches or differs from what's needed.

### 4.2 Generating Gap Analysis

1. Open a job application
2. Click **Generate Gap Analysis**
3. Wait for processing (typically 30-60 seconds)
4. Review the results

### 4.3 Understanding Gap Analysis Results

The analysis shows:
- **Matching Skills**: Skills you have that match the job
- **Gap Skills**: Skills the job requires that you may lack
- **Suggestions**: Recommended actions to address gaps

---

## 5. Generating VPR

### 5.1 What is VPR?

VPR (Visual Past Resume) is a visual representation of your professional background, optimized for ATS (Applicant Tracking Systems) and recruiters.

### 5.2 Generating a VPR

1. Open a job application
2. Click **Generate VPR**
3. Wait for processing (typically 1-2 minutes)
4. View and download your VPR

### 5.3 VPR Versions

Each time you generate a VPR for an application, a new version is created. You can:
- View previous versions
- Compare versions
- Download any version

---

## 6. CV Tailoring

### 6.1 What is CV Tailoring?

CV Tailoring adapts your CV to match the specific job description, highlighting the most relevant experience and skills.

### 6.2 Generating a Tailored CV

1. Open a job application
2. Click **Generate Tailored CV**
3. Wait for processing (typically 1-2 minutes)
4. View and download your tailored CV

---

## 7. Cover Letters

### 7.1 What is a Cover Letter?

A cover letter is a personalized letter introducing yourself and explaining why you're a strong fit for the position.

### 7.2 Generating a Cover Letter

1. Open a job application
2. Click **Generate Cover Letter**
3. Wait for processing (typically 1-2 minutes)
4. Review and edit as needed
5. Download or copy to use

---

## 8. Interview Preparation

### 8.1 What is Interview Prep?

Interview Prep generates potential interview questions based on the job description and your background, with suggested answer approaches.

### 8.2 Generating Interview Prep

1. Open a job application
2. Click **Generate Interview Prep**
3. Wait for processing (typically 1-2 minutes)
4. Review the questions and suggestions

### 8.3 Using Interview Prep

- Review each question
- Practice your answers
- Focus on questions where you feel less confident

---

## 9. Trial & Billing

### 9.1 Trial Period

**You get:**
- 14 days of full access
- 3 job applications (generations)

**Starting your trial:**
- Trial begins when you create your first application
- You'll see countdown timers on your dashboard

### 9.2 Tracking Usage

On your dashboard, you can see:
- **Days Remaining**: How many days left in trial
- **Applications Used**: How many of 3 used
- **Applications Remaining**: How many you can still create

### 9.3 Upgrading

When your trial ends or applications are exhausted:

1. Go to **Settings** > **Billing**
2. Select a plan:
   - **Monthly**: $20/month (unlimited applications)
   - **Annual**: $192/year ($16/month - save 20%)
3. Enter payment details
4. Confirm upgrade

---

## 10. Troubleshooting

### 10.1 Common Issues

#### "Session Expired" or "Please Login"
- Your session has timed out
- Simply log in again

#### "Upload Failed"
- Check file format (PDF, DOCX, TXT only)
- Ensure file is under 10MB
- Try again with a different browser

#### "Generation Failed"
- Check your trial status
- Ensure you have applications remaining
- Try again in a few minutes

#### "Error Processing Request"
- This may be a temporary issue
- Try again after a short wait
- If persists, contact support

### 10.2 Getting Help

If you encounter issues:

1. Check this guide for solutions
2. Contact support through the app
3. Email: support@careervp.com

---

## Appendix: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Application |
| Ctrl+S | Save Draft |
| Escape | Close Dialog |

---

## Appendix: API Endpoints Reference

| Endpoint | Description |
|----------|-------------|
| POST /auth/register | Create account |
| POST /auth/login | Login |
| POST /auth/refresh | Refresh token |
| GET /users/me | Get profile |
| GET/POST /cvs | List/Upload CVs |
| GET/POST /jobs | List/Create jobs |
| POST /gap-analysis/generate | Generate gap analysis |
| POST /vpr/generate | Generate VPR |
| POST /cv-tailoring/generate | Generate tailored CV |
| POST /cover-letter/generate | Generate cover letter |
| POST /interview-prep/generate | Generate interview prep |
