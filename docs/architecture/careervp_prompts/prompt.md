# 📊 **VALUE PROPOSITION REPORT: JSON SCHEMA & PROMPT GROUND TRUTH**

---

## **PART 1: COMPLETE JSON SCHEMA FOR VALUE PROPOSITION REPORT (VPR)**

### **JSON Structure Overview**

The Value Proposition Report follows a structured JSON format that enables systematic analysis of job posting requirements against candidate qualifications. This schema serves as ground truth for validation.

---

### **COMPLETE JSON SCHEMA**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ValuePropositionReport",
  "description": "Comprehensive analysis mapping candidate qualifications to job requirements with evidence-based positioning strategy",
  "type": "object",
  "required": [
    "metadata",
    "executiveSummary",
    "roleAlignment",
    "experienceMapping",
    "skillsAnalysis",
    "evidenceGaps",
    "differentiators",
    "concernsAndMitigations",
    "valueProposition",
    "applicationStrategy"
  ],
  "properties": {
    
    "metadata": {
      "type": "object",
      "description": "Report generation metadata and context",
      "required": ["reportDate", "candidateName", "targetRole", "targetCompany", "reportVersion"],
      "properties": {
        "reportDate": {
          "type": "string",
          "format": "date",
          "description": "ISO 8601 date when report was generated",
          "example": "2026-03-28"
        },
        "candidateName": {
          "type": "string",
          "description": "Full name of candidate",
          "example": "Yitzchak Meirovich"
        },
        "targetRole": {
          "type": "string",
          "description": "Exact job title from posting",
          "example": "Learning Experience Specialist"
        },
        "targetCompany": {
          "type": "string",
          "description": "Company name",
          "example": "SysAid Technologies"
        },
        "reportVersion": {
          "type": "string",
          "description": "Version number for tracking iterations",
          "pattern": "^\\d+\\.\\d+$",
          "example": "1.0"
        },
        "jobPostingURL": {
          "type": "string",
          "format": "uri",
          "description": "Optional URL to original job posting",
          "example": "https://careers.sysaid.com/jobs/learning-experience-specialist"
        },
        "analysisScope": {
          "type": "string",
          "enum": ["full", "preliminary", "targeted"],
          "description": "Depth of analysis performed",
          "default": "full"
        }
      }
    },

    "executiveSummary": {
      "type": "object",
      "description": "High-level fit assessment and positioning summary",
      "required": ["overallFitScore", "fitRationale", "topThreeStrengths", "topThreeConcerns", "recommendedApproach"],
      "properties": {
        "overallFitScore": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100,
          "description": "Percentage fit score (0-100) based on requirement alignment",
          "example": 85
        },
        "fitRationale": {
          "type": "string",
          "minLength": 100,
          "maxLength": 500,
          "description": "2-3 sentence explanation of fit score calculation",
          "example": "Strong alignment on technical instruction, AI platform development, and L&D strategy. Gap exists in ITSM domain-specific experience, mitigated by transferable SaaS training background. Overall fit is high due to builder-educator positioning and quantified outcomes."
        },
        "topThreeStrengths": {
          "type": "array",
          "minItems": 3,
          "maxItems": 3,
          "description": "Three strongest alignment points (most compelling selling points)",
          "items": {
            "type": "object",
            "required": ["strength", "evidence", "relevanceToRole"],
            "properties": {
              "strength": {
                "type": "string",
                "description": "Concise statement of strength (10-15 words)",
                "example": "Built operational AI platform (PresGen) demonstrating hands-on AI implementation capability"
              },
              "evidence": {
                "type": "string",
                "description": "Specific quantified proof point",
                "example": "PresGen achieves 60-90% content development time reduction, integrates OpenAI/Gemini/Anthropic LLMs, serves production users"
              },
              "relevanceToRole": {
                "type": "string",
                "description": "Direct connection to job requirement",
                "example": "Job requires AI expertise for SysAid Copilot training - PresGen proves ability to teach from production AI experience, not theory"
              }
            }
          }
        },
        "topThreeConcerns": {
          "type": "array",
          "minItems": 3,
          "maxItems": 3,
          "description": "Three most significant gaps or concerns hiring manager might have",
          "items": {
            "type": "object",
            "required": ["concern", "severity", "mitigation"],
            "properties": {
              "concern": {
                "type": "string",
                "description": "Specific gap or weakness (10-15 words)",
                "example": "No direct ITSM (IT Service Management) domain experience"
              },
              "severity": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Impact level of this concern on candidacy",
                "example": "medium"
              },
              "mitigation": {
                "type": "string",
                "description": "Strategy to address or reframe concern",
                "example": "Frame as 'meta-skill': Built training programs across multiple technical domains (AWS, frontend dev, AI) - ITSM concepts are learnable, instructional design expertise is transferable"
              }
            }
          }
        },
        "recommendedApproach": {
          "type": "string",
          "enum": ["aggressive_apply", "apply_with_customization", "apply_after_preparation", "do_not_apply"],
          "description": "Strategic recommendation for application",
          "example": "apply_with_customization"
        }
      }
    },

    "roleAlignment": {
      "type": "object",
      "description": "Detailed breakdown of role requirements vs. candidate qualifications",
      "required": ["coreResponsibilities", "requirementBreakdown"],
      "properties": {
        "coreResponsibilities": {
          "type": "array",
          "minItems": 1,
          "description": "Primary job responsibilities extracted from posting",
          "items": {
            "type": "object",
            "required": ["responsibility", "alignmentScore", "candidateEvidence"],
            "properties": {
              "responsibility": {
                "type": "string",
                "description": "Exact or paraphrased responsibility from job posting",
                "example": "Build customer training portal and Academy from scratch (greenfield initiative)"
              },
              "alignmentScore": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Percentage alignment (0-100) for this specific responsibility",
                "example": 90
              },
              "candidateEvidence": {
                "type": "array",
                "minItems": 1,
                "description": "Specific proof points from candidate background",
                "items": {
                  "type": "string",
                  "example": "Built AllCloud AWS training partner program from zero to $1M+ revenue, designed curriculum structure, delivered across 6 countries"
                }
              },
              "evidenceQuality": {
                "type": "string",
                "enum": ["direct", "analogous", "transferable", "weak"],
                "description": "How closely evidence matches requirement",
                "example": "direct"
              }
            }
          }
        },
        "requirementBreakdown": {
          "type": "object",
          "description": "Categorized requirements analysis",
          "required": ["mustHave", "niceToHave", "assumedPrerequisites"],
          "properties": {
            "mustHave": {
              "type": "array",
              "description": "Explicitly stated required qualifications",
              "items": {
                "type": "object",
                "required": ["requirement", "candidateMeetsRequirement", "evidence"],
                "properties": {
                  "requirement": {
                    "type": "string",
                    "example": "Experience building training programs/academies"
                  },
                  "candidateMeetsRequirement": {
                    "type": "boolean",
                    "example": true
                  },
                  "evidence": {
                    "type": "string",
                    "example": "AllCloud AWS Training Partner program: built from scratch, generated $1M+ revenue, achieved 90%+ certification pass rates"
                  },
                  "strengthOfEvidence": {
                    "type": "string",
                    "enum": ["strong", "moderate", "weak", "none"],
                    "example": "strong"
                  }
                }
              }
            },
            "niceToHave": {
              "type": "array",
              "description": "Preferred but not required qualifications",
              "items": {
                "type": "object",
                "required": ["preference", "candidateHasThis"],
                "properties": {
                  "preference": {
                    "type": "string",
                    "example": "LMS implementation experience (Cloud Academy, Udemy, etc.)"
                  },
                  "candidateHasThis": {
                    "type": "boolean",
                    "example": true
                  },
                  "evidence": {
                    "type": "string",
                    "example": "Implemented Cloud Academy LMS for 200+ users at AllCloud"
                  }
                }
              }
            },
            "assumedPrerequisites": {
              "type": "array",
              "description": "Implicit requirements not explicitly stated in posting",
              "items": {
                "type": "object",
                "required": ["assumption", "candidateMeetsThis", "reasoning"],
                "properties": {
                  "assumption": {
                    "type": "string",
                    "example": "Ability to work in fast-paced startup environment"
                  },
                  "candidateMeetsThis": {
                    "type": "boolean",
                    "example": true
                  },
                  "reasoning": {
                    "type": "string",
                    "example": "16 years at government (structured) + startup experience at AllCloud (agile, revenue-focused) demonstrates adaptability"
                  }
                }
              }
            }
          }
        }
      }
    },

    "experienceMapping": {
      "type": "object",
      "description": "Chronological experience mapped to job requirements",
      "required": ["relevantExperiences", "experienceGaps"],
      "properties": {
        "relevantExperiences": {
          "type": "array",
          "minItems": 1,
          "description": "Past roles/projects most relevant to target role",
          "items": {
            "type": "object",
            "required": ["role", "organization", "duration", "keyAchievements", "relevanceToTargetRole"],
            "properties": {
              "role": {
                "type": "string",
                "example": "Director of AWS Training"
              },
              "organization": {
                "type": "string",
                "example": "AllCloud"
              },
              "duration": {
                "type": "string",
                "pattern": "^\\d+(\\.\\d+)? (year|years|month|months)$",
                "example": "3 years"
              },
              "keyAchievements": {
                "type": "array",
                "minItems": 1,
                "description": "Quantified outcomes from this role",
                "items": {
                  "type": "object",
                  "required": ["achievement", "metric", "impact"],
                  "properties": {
                    "achievement": {
                      "type": "string",
                      "example": "Built AWS Training Partner program from zero"
                    },
                    "metric": {
                      "type": "string",
                      "example": "$1M+ annual revenue"
                    },
                    "impact": {
                      "type": "string",
                      "example": "Established AllCloud as top-tier AWS training provider across 6 countries"
                    }
                  }
                }
              },
              "relevanceToTargetRole": {
                "type": "string",
                "description": "Direct connection to SysAid Learning Experience Specialist responsibilities",
                "example": "Demonstrates greenfield training program build capability - exactly what SysAid needs for customer Academy launch"
              },
              "relevanceScore": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "How relevant this experience is (0-100)",
                "example": 95
              }
            }
          }
        },
        "experienceGaps": {
          "type": "array",
          "description": "Types of experience candidate lacks",
          "items": {
            "type": "object",
            "required": ["missingExperience", "impactOnCandidacy", "compensatingFactors"],
            "properties": {
              "missingExperience": {
                "type": "string",
                "example": "Direct ITSM domain experience (IT Service Management)"
              },
              "impactOnCandidacy": {
                "type": "string",
                "enum": ["critical", "significant", "moderate", "minimal"],
                "example": "moderate"
              },
              "compensatingFactors": {
                "type": "array",
                "description": "What candidate has that offsets this gap",
                "items": {
                  "type": "string",
                  "example": "Strong SaaS technical training background (AWS, frontend dev) - demonstrates ability to learn complex technical domains quickly"
                }
              },
              "mitigationStrategy": {
                "type": "string",
                "description": "How to address in application materials",
                "example": "Frame as transferable skill: 'Built training for multiple technical domains (cloud, dev, AI) - ITSM concepts are learnable, instructional design expertise is proven'"
              }
            }
          }
        }
      }
    },

    "skillsAnalysis": {
      "type": "object",
      "description": "Technical and soft skills mapping",
      "required": ["technicalSkills", "softSkills", "toolProficiency"],
      "properties": {
        "technicalSkills": {
          "type": "array",
          "description": "Technical competencies required for role",
          "items": {
            "type": "object",
            "required": ["skill", "requiredLevel", "candidateLevel", "evidence"],
            "properties": {
              "skill": {
                "type": "string",
                "example": "Instructional Design"
              },
              "requiredLevel": {
                "type": "string",
                "enum": ["expert", "advanced", "intermediate", "basic"],
                "example": "advanced"
              },
              "candidateLevel": {
                "type": "string",
                "enum": ["expert", "advanced", "intermediate", "basic", "none"],
                "example": "expert"
              },
              "evidence": {
                "type": "string",
                "example": "27 years technical instruction, designed multi-tier certification frameworks, implemented Cloud Academy LMS for 200+ users"
              },
              "gap": {
                "type": "boolean",
                "description": "True if candidate level below required level",
                "example": false
              },
              "developmentPath": {
                "type": "string",
                "description": "If gap exists, how to close it (optional)",
                "example": ""
              }
            }
          }
        },
        "softSkills": {
          "type": "array",
          "description": "Interpersonal and professional competencies",
          "items": {
            "type": "object",
            "required": ["skill", "candidateDemonstrates", "evidence"],
            "properties": {
              "skill": {
                "type": "string",
                "example": "Stakeholder Management"
              },
              "candidateDemonstrates": {
                "type": "boolean",
                "example": true
              },
              "evidence": {
                "type": "string",
                "example": "Delivered training across 6 countries, coordinated with sales/CS teams for customer success outcomes"
              },
              "strengthLevel": {
                "type": "string",
                "enum": ["exceptional", "strong", "adequate", "developing"],
                "example": "strong"
              }
            }
          }
        },
        "toolProficiency": {
          "type": "array",
          "description": "Specific tools/platforms mentioned in job posting or assumed necessary",
          "items": {
            "type": "object",
            "required": ["tool", "requiredForRole", "candidateProficiency"],
            "properties": {
              "tool": {
                "type": "string",
                "example": "LMS platforms (Cloud Academy, Udemy, AWS Skillbuilder)"
              },
              "requiredForRole": {
                "type": "boolean",
                "description": "Is this explicitly required or just helpful?",
                "example": true
              },
              "candidateProficiency": {
                "type": "string",
                "enum": ["expert", "proficient", "familiar", "none"],
                "example": "proficient"
              },
              "evidence": {
                "type": "string",
                "example": "Implemented Cloud Academy LMS for 200+ AllCloud users, familiar with AWS Skillbuilder, Udemy course structures"
              },
              "needsUpskilling": {
                "type": "boolean",
                "example": false
              }
            }
          }
        }
      }
    },

    "evidenceGaps": {
      "type": "object",
      "description": "Analysis of where candidate lacks documented proof",
      "required": ["identifiedGaps", "priorityGapsToAddress"],
      "properties": {
        "identifiedGaps": {
          "type": "array",
          "minItems": 1,
          "description": "All evidence gaps discovered during analysis",
          "items": {
            "type": "object",
            "required": ["requirement", "currentEvidence", "gapSeverity", "suggestedEvidence"],
            "properties": {
              "requirement": {
                "type": "string",
                "example": "Experience with gamification in learning programs"
              },
              "currentEvidence": {
                "type": "string",
                "description": "What candidate currently has (if anything)",
                "example": "None documented in CV or portfolio"
              },
              "gapSeverity": {
                "type": "string",
                "enum": ["critical", "high", "medium", "low"],
                "description": "How much this gap hurts candidacy",
                "example": "medium"
              },
              "suggestedEvidence": {
                "type": "array",
                "description": "Recommendations for what to add/create",
                "items": {
                  "type": "string",
                  "example": "Create gamification case study from PresGen-Assess module (badge system, progress tracking, adaptive assessments)"
                }
              },
              "canBeCreatedQuickly": {
                "type": "boolean",
                "description": "Can this evidence be generated before application?",
                "example": true
              },
              "estimatedTimeToCreate": {
                "type": "string",
                "pattern": "^\\d+(-\\d+)? (hour|hours|day|days|week|weeks)$",
                "example": "2-3 hours"
              }
            }
          }
        },
        "priorityGapsToAddress": {
          "type": "array",
          "minItems": 1,
          "maxItems": 5,
          "description": "Top gaps to address before applying (ranked by impact)",
          "items": {
            "type": "object",
            "required": ["gap", "priority", "actionItem"],
            "properties": {
              "gap": {
                "type": "string",
                "example": "No documented ITSM/customer academy examples"
              },
              "priority": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": "Priority ranking (1 = highest)",
                "example": 1
              },
              "actionItem": {
                "type": "string",
                "description": "Specific task to close this gap",
                "example": "Research SysAid Copilot documentation, create sample training module outline showing how you'd structure the Academy"
              },
              "deadline": {
                "type": "string",
                "enum": ["before_application", "before_interview", "nice_to_have"],
                "example": "before_application"
              }
            }
          }
        }
      }
    },

    "differentiators": {
      "type": "object",
      "description": "What makes candidate uniquely valuable vs. other applicants",
      "required": ["uniqueStrengths", "competitiveAdvantages", "positioningStatement"],
      "properties": {
        "uniqueStrengths": {
          "type": "array",
          "minItems": 1,
          "maxItems": 5,
          "description": "Capabilities most candidates won't have",
          "items": {
            "type": "object",
            "required": ["strength", "rarity", "relevance", "proof"],
            "properties": {
              "strength": {
                "type": "string",
                "example": "Built operational AI platform (PresGen) - not just taught about AI, but developed production AI system"
              },
              "rarity": {
                "type": "string",
                "enum": ["very_rare", "uncommon", "somewhat_rare"],
                "description": "How many other candidates likely have this?",
                "example": "very_rare"
              },
              "relevance": {
                "type": "string",
                "description": "Why this matters for SysAid role",
                "example": "SysAid needs someone to train customers on AI Copilot - teaching from production AI experience vs. theoretical knowledge is massive credibility boost"
              },
              "proof": {
                "type": "string",
                "example": "PresGen integrates OpenAI, Gemini, Anthropic LLMs; includes presentation generation, video processing, adaptive assessments; serves production users"
              }
            }
          }
        },
        "competitiveAdvantages": {
          "type": "array",
          "description": "Strategic positioning advantages",
          "items": {
            "type": "object",
            "required": ["advantage", "vsTypicalCandidate"],
            "properties": {
              "advantage": {
                "type": "string",
                "example": "Builder-Educator hybrid profile"
              },
              "vsTypicalCandidate": {
                "type": "string",
                "description": "How this beats typical competitor",
                "example": "Most L&D specialists teach about technology. Candidate BUILDS technology (40+ web apps at Ministry of Finance, PresGen AI platform) AND teaches about it - rare combination"
              },
              "howToLeverageInApplication": {
                "type": "string",
                "example": "Lead cover letter with: 'I don't just teach AI - I build AI platforms. Here's why that matters for your customer Academy...'"
              }
            }
          }
        },
        "positioningStatement": {
          "type": "string",
          "minLength": 100,
          "maxLength": 300,
          "description": "One-paragraph positioning to use in cover letter opening or LinkedIn summary",
          "example": "I'm a builder-educator: someone who teaches from hands-on technical experience, not theory alone. Over 27 years, I've built production systems (40+ web applications, AI platform serving users) and training programs generating $1M+ revenue with 90%+ certification pass rates. For SysAid's customer Academy, this means I can design training that resonates with technical admins because I've been in their shoes - configuring systems, troubleshooting issues, optimizing workflows."
        }
      }
    },

    "concernsAndMitigations": {
      "type": "object",
      "description": "Anticipated objections and how to address them",
      "required": ["likelyObjections", "preemptiveResponses"],
      "properties": {
        "likelyObjections": {
          "type": "array",
          "minItems": 1,
          "description": "Concerns hiring manager will probably have",
          "items": {
            "type": "object",
            "required": ["objection", "likelihood", "mitigation"],
            "properties": {
              "objection": {
                "type": "string",
                "example": "Candidate has no ITSM domain experience"
              },
              "likelihood": {
                "type": "string",
                "enum": ["very_likely", "likely", "possible", "unlikely"],
                "example": "very_likely"
              },
              "mitigation": {
                "type": "object",
                "required": ["strategy", "messaging"],
                "properties": {
                  "strategy": {
                    "type": "string",
                    "enum": ["reframe", "acknowledge_and_address", "provide_evidence", "show_analogous_experience"],
                    "example": "reframe"
                  },
                  "messaging": {
                    "type": "string",
                    "example": "ITSM is a domain I'll learn quickly (as I've done with cloud, frontend dev, AI). What I bring is proven ability to build training programs that drive measurable outcomes - that's the hard part. ITSM concepts are the easy part."
                  }
                }
              },
              "whereToAddress": {
                "type": "array",
                "description": "Which application materials should address this",
                "items": {
                  "type": "string",
                  "enum": ["cover_letter", "cv", "portfolio", "interview"],
                  "example": "cover_letter"
                }
              }
            }
          }
        },
        "preemptiveResponses": {
          "type": "array",
          "description": "Proactive ways to neutralize concerns before they're raised",
          "items": {
            "type": "object",
            "required": ["concern", "preemptiveAction"],
            "properties": {
              "concern": {
                "type": "string",
                "example": "Will candidate understand SysAid's product well enough to train customers?"
              },
              "preemptiveAction": {
                "type": "string",
                "example": "Complete home assignment thoroughly, demonstrating deep dive into SysAid AI documentation and ability to create training content without product access - shows self-directed learning capability"
              }
            }
          }
        }
      }
    },

    "valueProposition": {
      "type": "object",
      "description": "Clear articulation of value candidate brings to role",
      "required": ["primaryValue", "secondaryValues", "quantifiedImpact", "elevatorPitch"],
      "properties": {
        "primaryValue": {
          "type": "object",
          "required": ["statement", "evidence", "outcomeForSysAid"],
          "description": "Single most compelling reason to hire this candidate",
          "properties": {
            "statement": {
              "type": "string",
              "example": "I build training programs that generate measurable business outcomes, not just completion certificates"
            },
            "evidence": {
              "type": "string",
              "example": "AllCloud program: $1M+ revenue, 90%+ certification pass rates, delivered across 6 countries. PresGen: 60-90% content development time reduction."
            },
            "outcomeForSysAid": {
              "type": "string",
              "example": "SysAid's customer Academy will drive ticket reduction, product adoption, and revenue - I've built programs that hit all three KPIs"
            }
          }
        },
        "secondaryValues": {
          "type": "array",
          "minItems": 2,
          "maxItems": 4,
          "description": "Additional compelling selling points",
          "items": {
            "type": "object",
            "required": ["value", "proof"],
            "properties": {
              "value": {
                "type": "string",
                "example": "Deep AI expertise from building production AI platform"
              },
              "proof": {
                "type": "string",
                "example": "PresGen integrates OpenAI, Gemini, Anthropic - I teach AI from hands-on experience, not theoretical knowledge"
              }
            }
          }
        },
        "quantifiedImpact": {
          "type": "array",
          "description": "Specific metrics candidate can deliver for SysAid",
          "items": {
            "type": "object",
            "required": ["metric", "expectedRange", "basisForProjection"],
            "properties": {
              "metric": {
                "type": "string",
                "example": "Academy enrollment rate"
              },
              "expectedRange": {
                "type": "string",
                "example": "200+ customers enrolled in first 90 days"
              },
              "basisForProjection": {
                "type": "string",
                "example": "At AllCloud, training programs achieved 200+ enrollments within first quarter of launch across similar SaaS customer base"
              }
            }
          }
        },
        "elevatorPitch": {
          "type": "string",
          "minLength": 100,
          "maxLength": 200,
          "description": "30-second pitch summarizing entire value proposition",
          "example": "I've spent 27 years building training programs that drive business outcomes: $1M+ revenue at AllCloud, 90%+ certification pass rates, reduced support tickets 40% through effective enablement. I also build technology - AI platforms, web applications - so I teach from hands-on experience, not theory. For SysAid's customer Academy, that means training that resonates with technical admins and delivers measurable ROI."
        }
      }
    },

    "applicationStrategy": {
      "type": "object",
      "description": "Tactical recommendations for application execution",
      "required": ["cvCustomization", "coverLetterStructure", "linkedInOutreach", "interviewPreparation"],
      "properties": {
        "cvCustomization": {
          "type": "object",
          "required": ["leadWithDifferentiator", "keywordOptimization", "quantificationPriorities"],
          "properties": {
            "leadWithDifferentiator": {
              "type": "string",
              "description": "What should appear first on CV to grab attention",
              "example": "Open with: 'Builder-Educator | Built $1M+ AWS Training Program + Production AI Platform' - immediately signals unique positioning"
            },
            "keywordOptimization": {
              "type": "array",
              "description": "Keywords to bold/emphasize for ATS",
              "items": {
                "type": "string",
                "example": "Learning Experience Design"
              }
            },
            "quantificationPriorities": {
              "type": "array",
              "description": "Which numbers to emphasize most",
              "items": {
                "type": "object",
                "required": ["metric", "context", "placement"],
                "properties": {
                  "metric": {
                    "type": "string",
                    "example": "$1M+ revenue"
                  },
                  "context": {
                    "type": "string",
                    "example": "AllCloud AWS Training Partner program annual revenue"
                  },
                  "placement": {
                    "type": "string",
                    "enum": ["opening_summary", "experience_bullets", "both"],
                    "example": "both"
                  }
                }
              }
            },
            "sectionsToCompress": {
              "type": "array",
              "description": "Which CV sections to minimize for space",
              "items": {
                "type": "string",
                "example": "Ministry of Finance experience (compress to 2-3 bullets, focus on relevant technical training aspects)"
              }
            }
          }
        },
        "coverLetterStructure": {
          "type": "object",
          "required": ["openingHook", "paragraphBreakdown", "closingCTA"],
          "properties": {
            "openingHook": {
              "type": "string",
              "minLength": 50,
              "maxLength": 150,
              "description": "First sentence to grab attention",
              "example": "I don't just teach AI - I build AI platforms. Here's why that matters for SysAid's customer Academy launch."
            },
            "paragraphBreakdown": {
              "type": "array",
              "minItems": 3,
              "maxItems": 3,
              "description": "Three-paragraph structure (standard for cover letters)",
              "items": {
                "type": "object",
                "required": ["paragraphNumber", "purpose", "keyPoints"],
                "properties": {
                  "paragraphNumber": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 3,
                    "example": 1
                  },
                  "purpose": {
                    "type": "string",
                    "example": "Establish unique positioning (builder-educator)"
                  },
                  "keyPoints": {
                    "type": "array",
                    "items": {
                      "type": "string",
                      "example": "Built PresGen AI platform (production system, not just taught about AI)"
                    }
                  }
                }
              }
            },
            "closingCTA": {
              "type": "string",
              "description": "Call-to-action in final paragraph",
              "example": "I'd welcome the chance to discuss how my builder-educator background can accelerate SysAid's customer Academy from concept to measurable impact. Can we schedule a conversation?"
            }
          }
        },
        "linkedInOutreach": {
          "type": "object",
          "required": ["targetContacts", "messageTemplate", "timing"],
          "properties": {
            "targetContacts": {
              "type": "array",
              "description": "Who to reach out to on LinkedIn",
              "items": {
                "type": "object",
                "required": ["role", "rationale"],
                "properties": {
                  "role": {
                    "type": "string",
                    "example": "Hiring Manager (if identifiable)"
                  },
                  "rationale": {
                    "type": "string",
                    "example": "Direct decision-maker; personalized outreach shows initiative and allows you to address fit questions proactively"
                  },
                  "findingStrategy": {
                    "type": "string",
                    "example": "LinkedIn search: 'SysAid' + 'Learning' OR 'Training' OR 'Customer Success'; filter by current employees"
                  }
                }
              }
            },
            "messageTemplate": {
              "type": "string",
              "minLength": 100,
              "maxLength": 300,
              "description": "Suggested LinkedIn connection request or InMail message",
              "example": "Hi [Name], I just applied for the Learning Experience Specialist role at SysAid. I've built training programs generating $1M+ revenue and reduced support tickets 40% through effective enablement - exactly the outcomes SysAid's customer Academy should deliver. I'd love to briefly discuss how my builder-educator background aligns with what you're looking for. Are you open to a quick chat?"
            },
            "timing": {
              "type": "string",
              "enum": ["before_application", "same_day_as_application", "1-2_days_after_application", "after_no_response_2_weeks"],
              "example": "same_day_as_application"
            }
          }
        },
        "interviewPreparation": {
          "type": "object",
          "required": ["anticipatedQuestions", "questionsToAsk", "portfolioPieces"],
          "properties": {
            "anticipatedQuestions": {
              "type": "array",
              "description": "Questions hiring manager likely to ask",
              "items": {
                "type": "object",
                "required": ["question", "suggestedAnswer", "evidenceToProvide"],
                "properties": {
                  "question": {
                    "type": "string",
                    "example": "You don't have ITSM experience - how will you create training for a product you don't know?"
                  },
                  "suggestedAnswer": {
                    "type": "string",
                    "example": "Great question. I've built training for technologies I initially didn't know - AWS, frontend development frameworks, AI platforms - by immersing myself in the product, talking to users, and focusing on outcomes rather than just features. For this home assignment, I dove deep into SysAid AI documentation and created a certification blueprint without product access. That's exactly how I'd approach the Academy: learn the product deeply, understand customer pain points, design training that solves problems."
                  },
                  "evidenceToProvide": {
                    "type": "string",
                    "example": "Home assignment deliverables - show depth of SysAid AI understanding achieved through documentation review alone"
                  }
                }
              }
            },
            "questionsToAsk": {
              "type": "array",
              "description": "Questions candidate should ask to demonstrate strategic thinking",
              "items": {
                "type": "object",
                "required": ["question", "purpose"],
                "properties": {
                  "question": {
                    "type": "string",
                    "example": "What's the #1 customer pain point the Academy should solve in first 90 days?"
                  },
                  "purpose": {
                    "type": "string",
                    "example": "Shows outcome-focused mindset; reveals priorities to align answer with their goals"
                  }
                }
              }
            },
            "portfolioPieces": {
              "type": "array",
              "description": "Work samples to bring/share in interview",
              "items": {
                "type": "object",
                "required": ["piece", "relevance", "format"],
                "properties": {
                  "piece": {
                    "type": "string",
                    "example": "PresGen platform demo"
                  },
                  "relevance": {
                    "type": "string",
                    "example": "Demonstrates AI expertise, builder credibility, ability to explain complex technology simply"
                  },
                  "format": {
                    "type": "string",
                    "enum": ["live_demo", "video_recording", "screenshots", "written_case_study"],
                    "example": "live_demo"
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

---

## **PART 2: PROMPTS USED TO GENERATE VALUE PROPOSITION REPORT**

### **VPR Generation Workflow: Three-Phase Prompt Architecture**

The Value Proposition Report generation follows a structured three-phase approach with specific prompts at each stage. These prompts serve as ground truth for consistent VPR generation.

---

### **PHASE 1: GAP ANALYSIS & CLARIFYING QUESTIONS**

**Prompt 1.1: Initial Gap Analysis**

```
You are an expert job application strategist helping a candidate apply for a role. Your task is to perform an initial gap analysis before creating any application materials.

INPUTS PROVIDED:
- Job posting: [FULL JOB POSTING TEXT]
- Candidate background: [CV, PORTFOLIO LINKS, KEY ACHIEVEMENTS]

TASK:
Analyze the job posting and candidate background to identify:

1. EVIDENCE GAPS: What proof points does the candidate lack?
   - List specific requirements from job posting
   - Note which requirements candidate has NO documented evidence for
   - Assess severity of each gap (critical/high/medium/low)

2. CLARIFYING QUESTIONS: What information do you need before proceeding?
   - Questions about candidate's undocumented experience
   - Questions about job posting interpretation
   - Questions about application constraints (timeline, format preferences)

OUTPUT FORMAT:
## Evidence Gaps
[List each gap with requirement → current evidence → severity]

## Clarifying Questions
[Numbered list of questions, grouped by category]

CONSTRAINTS:
- Do NOT make assumptions about missing information
- Do NOT create application materials yet
- Flag any job requirements that seem ambiguous or could be interpreted multiple ways
- Prioritize questions by impact on application strategy
```

**Prompt 1.2: Clarifying Question Response Processing**

```
Based on the candidate's answers to clarifying questions, update your understanding:

CLARIFYING QUESTIONS ASKED:
[List of questions from Prompt 1.1]

CANDIDATE RESPONSES:
[Candidate's answers]

TASK:
1. Integrate new information into candidate profile
2. Identify remaining gaps (what's still missing after clarification)
3. Assess whether sufficient information now exists to create strong application materials
4. Flag any red flags or dealbreakers discovered

OUTPUT FORMAT:
## Updated Candidate Profile
[Incorporate new information]

## Remaining Evidence Gaps
[What's still missing]

## Application Viability Assessment
- Overall fit score (0-100): [score]
- Recommendation: [Apply Now / Apply After Preparation / Do Not Apply]
- Rationale: [2-3 sentences]

## Red Flags / Concerns
[List any dealbreakers or significant concerns]
```

---

### **PHASE 2: VALUE PROPOSITION REPORT GENERATION**

**Prompt 2.1: Generate Complete VPR**

```
You are an expert job application strategist. Generate a comprehensive Value Proposition Report (VPR) that analyzes the candidate's fit for the target role and provides strategic guidance for application.

INPUTS:
- Job posting: [FULL TEXT]
- Candidate background: [CV, achievements, clarifying Q&A responses]
- Previous gap analysis: [From Phase 1]

OUTPUT: Complete JSON object following the ValuePropositionReport schema

CRITICAL REQUIREMENTS:

1. EVIDENCE-BASED ANALYSIS ONLY
   - Every claim must be supported by documented candidate experience
   - No invented achievements or exaggerated capabilities
   - Flag gaps honestly rather than papering over them

2. SPECIFICITY OVER GENERALIZATION
   - Use exact numbers (e.g., "$1M+ revenue" not "significant revenue")
   - Quote specific job posting requirements (don't paraphrase vaguely)
   - Provide concrete examples, not abstract competencies

3. STRATEGIC POSITIONING
   - Identify 1-2 unique differentiators (what makes this candidate stand out)
   - Anticipate hiring manager objections and provide mitigation strategies
   - Connect candidate strengths to business outcomes, not just job duties

4. ACTIONABLE RECOMMENDATIONS
   - Application strategy must be specific (which keywords to bold, where to place metrics)
   - Interview preparation must include actual questions and suggested answers
   - Portfolio pieces must be concrete items candidate can prepare

5. JSON SCHEMA COMPLIANCE
   - All required fields must be populated
   - Enums must use exact values from schema
   - Scores (0-100) must be justified by evidence
   - Arrays must meet minItems/maxItems constraints

SCHEMA:
[Include complete JSON schema from Part 1]

TONE:
- Analytical and objective (this is strategic analysis, not marketing copy)
- Honest about gaps and concerns (helps candidate prepare, not hide weaknesses)
- Action-oriented (every insight should lead to specific application tactic)

OUTPUT:
Complete JSON object conforming to ValuePropositionReport schema
```

**Prompt 2.2: VPR Validation & Refinement**

```
You are reviewing a Value Proposition Report for quality and accuracy.

INPUT VPR:
[JSON object from Prompt 2.1]

VALIDATION CHECKLIST:

1. EVIDENCE VERIFICATION
   - Is every achievement claim backed by documented proof?
   - Are quantified metrics accurate (not inflated)?
   - Can candidate defend every statement in interview?

2. GAP HONESTY
   - Are significant weaknesses identified honestly?
   - Do mitigations address concerns substantively (not just excuse them)?
   - Is overall fit score justified by evidence?

3. STRATEGIC COHERENCE
   - Do differentiators align with job requirements?
   - Does application strategy emphasize actual strengths?
   - Are interview questions realistic (not strawmen)?

4. SCHEMA COMPLIANCE
   - All required fields present?
   - Enum values from allowed list?
   - String length constraints met?
   - Score ranges (0-100) appropriate?

5. ACTIONABILITY
   - Can candidate execute recommended CV customization?
   - Are LinkedIn outreach templates usable as-is?
   - Do interview prep answers provide genuine value?

OUTPUT:
## Validation Results
- Overall quality score (0-100): [score]
- Critical issues: [List dealbreakers]
- Recommended revisions: [Specific changes needed]

## Revised VPR
[Updated JSON if revisions made, otherwise original]
```

---

### **PHASE 3: APPLICATION MATERIALS GENERATION**

**Prompt 3.1: Generate ATS-Optimized CV**

```
Using the Value Proposition Report, generate an ATS-optimized CV tailored to the target role.

INPUT:
- VPR JSON: [Complete VPR from Phase 2]
- Master CV: [Candidate's full work history]
- Target ATS system: [Greenhouse / Lever / Workday / etc.]

REQUIREMENTS:

1. STRUCTURE
   - Single column layout (ATS-friendly)
   - Standard fonts (Arial, Calibri, Times New Roman)
   - No tables, text boxes, headers/footers
   - Sections: Summary → Experience → Education → Certifications → Skills

2. KEYWORD OPTIMIZATION
   - Bold keywords from job posting (as identified in VPR.applicationStrategy.cvCustomization.keywordOptimization)
   - Use exact terminology from job posting
   - Front-load important keywords in first 1/3 of document

3. QUANTIFICATION
   - Emphasize metrics from VPR.applicationStrategy.cvCustomization.quantificationPriorities
   - Every bullet point should include number, percentage, or measurable outcome where possible

4. DIFFERENTIATOR EMPHASIS
   - Lead with VPR.differentiators.positioningStatement (modified for CV summary format)
   - Experience bullets prioritize uniqueStrengths
   - Most relevant experience first (even if not most recent)

5. COMPRESSION STRATEGY
   - Compress sections identified in VPR.applicationStrategy.cvCustomization.sectionsToCompress
   - Target: 2 pages maximum
   - Older/less relevant roles: 1-2 bullets max

OUTPUT FORMAT: .docx file with strategic bold formatting for ATS optimization

EXAMPLE BOLD PATTERN:
"Built **AWS Training Partner program** generating **$1M+ annual revenue** with **90%+ certification pass rates** across **6 countries**"
```

**Prompt 3.2: Generate Cover Letter**

```
Using the Value Proposition Report, generate a compelling cover letter.

INPUT:
- VPR JSON: [Complete VPR from Phase 2]
- Company research: [Any additional company info beyond job posting]

REQUIREMENTS:

1. STRUCTURE: Three paragraphs (max 300-350 words total)
   - Para 1: Hook + positioning (VPR.applicationStrategy.coverLetterStructure.openingHook + VPR.differentiators.positioningStatement)
   - Para 2: Proof points (VPR.valueProposition.primaryValue + 2-3 secondary values)
   - Para 3: Forward-looking alignment + CTA (VPR.applicationStrategy.coverLetterStructure.closingCTA)

2. EVIDENCE-BASED CLAIMS
   - Every statement backed by specific achievement from VPR.experienceMapping.relevantExperiences
   - Use metrics from VPR.valueProposition.quantifiedImpact
   - No generic claims ("I'm a team player" ❌ / "I built training programs achieving 90%+ pass rates" ✅)

3. CONCERN MITIGATION
   - Address top concern from VPR.concernsAndMitigations.likelyObjections if severity is "high" or "very_likely"
   - Frame proactively (not defensively)
   - Use messaging from VPR.concernsAndMitigations.likelyObjections[].mitigation.messaging

4. TONE
   - Confident but not arrogant
   - Specific proof over vague competencies
   - Business-outcome focused (not "I want to learn" but "I will deliver X outcome")

5. FORMATTING
   - Standard business letter format
   - Bold 2-3 key phrases for emphasis (strategic bolding from VPR keywords)
   - Single-spaced, professional font

OUTPUT: .docx file with strategic bold formatting
```

**Prompt 3.3: Generate LinkedIn Outreach Message**

```
Using the Value Proposition Report, generate a LinkedIn connection request or InMail message to hiring manager.

INPUT:
- VPR JSON: [Complete VPR from Phase 2]
- Target contact: [From VPR.applicationStrategy.linkedInOutreach.targetContacts]

REQUIREMENTS:

1. LENGTH
   - Connection request: 200 characters max (LinkedIn limit)
   - InMail: 300 words max (but aim for 150-200 for readability)

2. CONTENT
   - Open with specific value proposition from VPR.valueProposition.elevatorPitch
   - Reference concrete achievement (1 metric from VPR.valueProposition.quantifiedImpact)
   - Connect achievement to company need (from job posting)
   - Clear ask (request conversation, not job)

3. TONE
   - Professional but conversational (peer-to-peer, not supplicant)
   - Confident in value, not desperate for opportunity
   - Specific to company/role (not generic template obviously)

4. TIMING
   - Follow timing guidance from VPR.applicationStrategy.linkedInOutreach.timing

OUTPUT FORMATS:

CONNECTION REQUEST (if <200 chars):
"[Message text]"

INMAIL MESSAGE:
Subject: [Compelling subject line]
Body: [Message text]

FOLLOW-UP MESSAGE (if no response after 2 weeks):
"[Brief follow-up text]"
```

**Prompt 3.4: Generate Interview Preparation Document**

```
Using the Value Proposition Report, generate a comprehensive interview preparation guide.

INPUT:
- VPR JSON: [Complete VPR from Phase 2]
- Job posting: [Full text]

OUTPUT STRUCTURE:

## ANTICIPATED QUESTIONS & ANSWERS (from VPR.applicationStrategy.interviewPreparation.anticipatedQuestions)

For each question:
1. Question: [Exact question hiring manager likely to ask]
2. Suggested Answer: [2-3 paragraph response using STAR format where appropriate]
3. Evidence to Mention: [Specific achievements to reference]
4. What NOT to Say: [Common mistakes to avoid]

Example format:
### Question 1: "You don't have ITSM experience - how will you create training for a product you don't know?"

**Suggested Answer:**
"Great question - this speaks to how I approach learning new domains. I've built training programs for technologies I initially didn't know: AWS (came from frontend dev background), AI platforms (came from web development), instructional design methodologies (came from technical instruction). 

My process: [1] Immerse in product documentation and talk to users to understand pain points, [2] Focus on outcomes rather than just features - what problem does this solve?, [3] Build training iteratively with user feedback. 

For this role specifically, I completed the home assignment by diving deep into SysAid AI documentation and created a certification blueprint without product access. That's exactly how I'd approach the Academy: learn the product deeply, design training that solves real customer problems."

**Evidence to Mention:**
- Home assignment deliverables (show depth of understanding)
- AllCloud AWS program (built training for 20+ AWS services)
- Ministry of Finance (learned new technologies every 6-12 months for 16 years)

**What NOT to Say:**
❌ "I'm a fast learner" (too vague)
❌ "ITSM seems pretty straightforward" (minimizes the domain)
❌ "I'll figure it out" (sounds unprepared)

## QUESTIONS TO ASK INTERVIEWER (from VPR.applicationStrategy.interviewPreparation.questionsToAsk)

For each question:
1. Question: [Exact wording]
2. Why Ask This: [Strategic purpose]
3. What to Listen For: [Key signals in their answer]

## PORTFOLIO PIECES TO PREPARE (from VPR.applicationStrategy.interviewPreparation.portfolioPieces)

For each piece:
1. Item: [What to prepare]
2. Format: [Live demo / video / screenshots / case study]
3. Key Points to Highlight: [What to emphasize]
4. Time Required: [How long to present]

## CONCERN MITIGATION STRATEGY

From VPR.concernsAndMitigations.likelyObjections:
- List top 3 concerns hiring manager likely has
- Proactive strategy to address each BEFORE they ask
- Specific evidence to neutralize concern

## COMPENSATION DISCUSSION PREP

- Research market rate for role (Glassdoor, Levels.fyi, Payscale)
- Current compensation: [Candidate's current total comp]
- Target range: [Based on market research + candidate's premium positioning]
- Justification: [Why candidate worth top of range - from VPR.differentiators]

OUTPUT: Formatted document (.docx) with sections above
```

---

## **PART 3: PROMPT USAGE GUIDELINES & VALIDATION RULES**

### **When to Use Each Prompt**

| Scenario | Prompts to Use | Order |
|----------|----------------|-------|
| **New job application (full process)** | All prompts 1.1 → 1.2 → 2.1 → 2.2 → 3.1 → 3.2 → 3.3 → 3.4 | Sequential |
| **VPR only (no materials yet)** | 1.1 → 1.2 → 2.1 → 2.2 | Stop after Phase 2 |
| **Update existing VPR with new info** | 1.2 (with updated responses) → 2.2 (validation) | Skip 1.1, 2.1 |
| **Generate materials from existing VPR** | 3.1 → 3.2 → 3.3 → 3.4 | Skip Phase 1-2 |
| **CV only (fast track)** | 3.1 with simplified VPR input | Single prompt |
| **Interview prep only** | 3.4 with VPR input | Single prompt |

---

### **Validation Rules for VPR Output**

#### **Rule 1: Evidence Traceability**
Every claim in the VPR must trace back to documented candidate experience.

**Validation Test:**
```python
def validate_evidence_traceability(vpr_json, candidate_cv):
    """
    For each achievement mentioned in VPR, verify it exists in CV or clarifying Q&A
    """
    achievements_in_vpr = extract_all_achievements(vpr_json)
    achievements_in_cv = extract_all_achievements(candidate_cv)
    
    for achievement in achievements_in_vpr:
        if achievement not in achievements_in_cv:
            flag_warning(f"Achievement '{achievement}' in VPR not found in source materials")
```

**Examples:**
- ✅ VALID: VPR says "$1M+ revenue" → CV shows "Built AWS Training Partner program generating $1M+ annual revenue"
- ❌ INVALID: VPR says "Reduced onboarding time 50%" → CV has no mention of onboarding metrics

---

#### **Rule 2: Quantification Consistency**
Metrics must be consistent across all VPR sections and match source materials.

**Validation Test:**
```python
def validate_metric_consistency(vpr_json):
    """
    Check that same achievement uses same metric across different VPR sections
    """
    # Extract "AllCloud revenue" metric from all sections
    exec_summary_metric = vpr_json['executiveSummary']['topThreeStrengths'][0]['evidence']
    experience_metric = vpr_json['experienceMapping']['relevantExperiences'][0]['keyAchievements'][0]['metric']
    value_prop_metric = vpr_json['valueProposition']['primaryValue']['evidence']
    
    # All should say "$1M+ revenue" not varying amounts
    assert all_metrics_match(exec_summary_metric, experience_metric, value_prop_metric)
```

**Examples:**
- ✅ VALID: All sections say "$1M+ revenue"
- ❌ INVALID: Executive summary says "$1M+", experience section says "$1.2M", value prop says "over $1 million"

---

#### **Rule 3: Alignment Score Justification**
Scores (0-100) must be justified by evidence quality and quantity.

**Scoring Rubric:**
```
ALIGNMENT SCORE CALCULATION:

90-100: Perfect match
- Direct experience in exact same role/responsibility
- Multiple quantified achievements proving capability
- No gaps or concerns
- Example: Candidate built AWS training program, role requires building customer training program

70-89: Strong match
- Analogous experience (different domain, same skills)
- 2+ quantified achievements
- Minor gaps with strong mitigation
- Example: Candidate built SaaS training, role requires ITSM training (transferable)

50-69: Moderate match
- Transferable experience (related but not direct)
- 1-2 achievements, some quantified
- Moderate gaps requiring preparation
- Example: Candidate did technical instruction, role requires instructional design

30-49: Weak match
- Tangential experience (some overlap)
- Limited achievements, mostly qualitative
- Significant gaps
- Example: Candidate taught in-person, role requires digital learning design

0-29: Poor match
- No relevant experience
- No documented achievements
- Critical gaps with no mitigation
- Example: Candidate has no L&D experience, role requires L&D expertise
```

**Validation Test:**
```python
def validate_alignment_scores(vpr_json):
    """
    Verify alignment scores match evidence quality
    """
    for responsibility in vpr_json['roleAlignment']['coreResponsibilities']:
        score = responsibility['alignmentScore']
        evidence_count = len(responsibility['candidateEvidence'])
        evidence_quality = responsibility['evidenceQuality']
        
        # High score requires strong evidence
        if score >= 90:
            assert evidence_quality == 'direct'
            assert evidence_count >= 2
        
        # Low score should reflect weak/missing evidence
        if score <= 49:
            assert evidence_quality in ['transferable', 'weak']
```

---

#### **Rule 4: Gap Severity Calibration**
Gap severity must match actual impact on candidacy.

**Severity Definitions:**
```
CRITICAL: Dealbreaker if not addressed before application
- Explicitly required qualification candidate completely lacks
- No compensating factors exist
- Example: Job requires AWS certification, candidate has none and can't get one before deadline

HIGH: Significantly weakens candidacy
- Strongly preferred qualification candidate lacks
- Weak compensating factors
- Example: Job wants LMS implementation experience, candidate has none but has general tech implementation background

MEDIUM: Noticeable gap but addressable
- Preferred qualification candidate lacks
- Strong compensating factors exist
- Example: Job wants ITSM domain experience, candidate has SaaS training experience (transferable)

LOW: Minor gap with negligible impact
- Nice-to-have qualification candidate lacks
- Multiple compensating factors
- Example: Job prefers Articulate Storyline experience, candidate uses Camtasia (similar tool)
```

**Validation Test:**
```python
def validate_gap_severity(vpr_json, job_posting):
    """
    Check gap severity matches requirement importance
    """
    for gap in vpr_json['evidenceGaps']['identifiedGaps']:
        requirement = gap['requirement']
        severity = gap['gapSeverity']
        
        # If requirement is in job posting "must have" section → gap should be HIGH or CRITICAL
        if is_must_have_requirement(requirement, job_posting):
            assert severity in ['critical', 'high']
        
        # If requirement is in "nice to have" section → gap should be LOW or MEDIUM
        if is_nice_to_have_requirement(requirement, job_posting):
            assert severity in ['low', 'medium']
```

---

#### **Rule 5: Differentiator Rarity Check**
"Unique" strengths must actually be rare among typical candidates.

**Rarity Definitions:**
```
VERY_RARE: <5% of candidates have this
- Built production AI platform (not just used AI tools)
- Generated $1M+ revenue from training program
- 90%+ certification pass rates sustained over years
- Published research or patents in field

UNCOMMON: 5-20% of candidates have this
- 10+ years specialized experience
- Delivered training across 5+ countries
- Built programs from scratch (greenfield initiatives)
- Expert-level tool proficiency (Articulate, advanced LMS)

SOMEWHAT_RARE: 20-40% of candidates have this
- 5+ years in L&D role
- Managed team of instructional designers
- Implemented LMS for organization
- Strong technical + teaching background
```

**Validation Test:**
```python
def validate_differentiator_rarity(vpr_json):
    """
    Verify "very_rare" differentiators are actually unique
    """
    for diff in vpr_json['differentiators']['uniqueStrengths']:
        if diff['rarity'] == 'very_rare':
            # Should be something <5% of L&D professionals have
            # Examples of valid very_rare: built AI platform, $1M+ revenue, 90%+ pass rates
            # Examples of invalid very_rare: "good communicator", "experienced trainer"
            assert is_genuinely_rare(diff['strength'])
```

---

#### **Rule 6: Mitigation Strategy Substance**
Concern mitigations must address root issue, not just deflect.

**Mitigation Quality Rubric:**
```
STRONG MITIGATION:
- Acknowledges concern directly
- Provides analogous evidence
- Reframes as strength or non-issue
- Example: "No ITSM experience" → "Built training for 3 complex technical domains (AWS, frontend, AI) - ITSM concepts learnable, instructional design expertise proven"

WEAK MITIGATION:
- Deflects or minimizes concern
- No supporting evidence
- Generic claims
- Example: "No ITSM experience" → "I'm a fast learner" ❌
```

**Validation Test:**
```python
def validate_mitigation_quality(vpr_json):
    """
    Check mitigations substantively address concerns
    """
    for objection in vpr_json['concernsAndMitigations']['likelyObjections']:
        mitigation = objection['mitigation']['messaging']
        
        # Strong mitigation should:
        # 1. Include specific evidence (metrics, achievements, examples)
        # 2. Reframe concern as strength or addressable gap
        # 3. Not use weak phrases ("I'm a fast learner", "I'll figure it out")
        
        assert has_specific_evidence(mitigation)
        assert not contains_weak_phrases(mitigation, ['fast learner', 'figure it out', 'willing to learn'])
```

---

### **Common VPR Generation Errors & Fixes**

| Error Type | Example | Fix |
|------------|---------|-----|
| **Fabricated Achievement** | VPR claims "reduced costs 40%" but CV has no cost reduction metric | Remove claim OR ask candidate for documentation |
| **Vague Positioning** | "Strong communicator with proven track record" | Replace with specific: "Delivered technical training to 500+ engineers across 6 countries" |
| **Inconsistent Metrics** | Executive summary says "$1M", experience says "$1.2M" | Standardize to one version (preferably conservative: "$1M+") |
| **Unjustified Score** | 95 alignment score but only 1 weak piece of evidence | Lower score to 60-70 OR find additional evidence |
| **Generic Differentiator** | "Passionate about learning" listed as unique strength | Replace with quantified unique capability |
| **Defensive Mitigation** | "I don't have X but I'm willing to learn" | Reframe with analogous evidence: "I've learned similar domains (list examples)" |

---

### **VPR Quality Checklist**

Before finalizing VPR, verify:

**Evidence Integrity:**
- [ ] Every metric traces to source document (CV, portfolio, clarifying Q&A)
- [ ] No invented achievements or exaggerated numbers
- [ ] Quantifications are defensible in interview

**Strategic Coherence:**
- [ ] Differentiators actually differentiate (not generic)
- [ ] Top concerns are realistic (what hiring manager will actually wonder)
- [ ] Mitigations address root issue substantively

**Actionability:**
- [ ] CV customization provides specific formatting instructions
- [ ] Cover letter structure gives actual paragraph breakdowns
- [ ] Interview prep includes real questions candidate will face
- [ ] LinkedIn message is ready to send (not just template)

**Schema Compliance:**
- [ ] All required fields populated
- [ ] Enums use exact allowed values
- [ ] Scores (0-100) are justified
- [ ] String lengths within constraints
- [ ] Arrays meet minItems/maxItems

**Business Alignment:**
- [ ] Value proposition connects to company outcomes (not just candidate desires)
- [ ] Quantified impact is realistic and measurable
- [ ] Positioning emphasizes what employer gets (not what candidate wants)

---

This completes the ground truth documentation for Value Proposition Report JSON schema and generation prompts. These specifications ensure consistent, high-quality VPR output that drives successful job applications.