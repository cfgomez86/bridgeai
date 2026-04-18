"use client"

import { useState } from "react"

export type WorkflowState = {
  projectId: string
  requirementText: string
  language: string
  requirementId: string | null
  intent: string | null
  featureType: string | null
  complexity: string | null
  keywords: string[]
  analysisId: string | null
  filesImpacted: number | null
  modulesImpacted: string[]
  riskLevel: string | null
  storyId: string | null
  storyTitle: string | null
  storyPoints: number | null
  currentStep: 1 | 2 | 3 | 4 | 5
}

const initialState: WorkflowState = {
  projectId: "my-project",
  requirementText: "",
  language: "es",
  requirementId: null,
  intent: null,
  featureType: null,
  complexity: null,
  keywords: [],
  analysisId: null,
  filesImpacted: null,
  modulesImpacted: [],
  riskLevel: null,
  storyId: null,
  storyTitle: null,
  storyPoints: null,
  currentStep: 1,
}

export function useWorkflow() {
  const [state, setState] = useState<WorkflowState>(initialState)

  function setProjectId(projectId: string) {
    setState((prev) => ({ ...prev, projectId }))
  }

  function setRequirementText(requirementText: string) {
    setState((prev) => ({ ...prev, requirementText }))
  }

  function setLanguage(language: string) {
    setState((prev) => ({ ...prev, language }))
  }

  function completeStep1(data: {
    requirementId: string
    intent: string
    featureType: string
    complexity: string
    keywords: string[]
  }) {
    setState((prev) => ({
      ...prev,
      requirementId: data.requirementId,
      intent: data.intent,
      featureType: data.featureType,
      complexity: data.complexity,
      keywords: data.keywords,
      currentStep: 2,
    }))
  }

  function completeStep2(data: {
    analysisId: string
    filesImpacted: number
    modulesImpacted: string[]
    riskLevel: string
  }) {
    setState((prev) => ({
      ...prev,
      analysisId: data.analysisId,
      filesImpacted: data.filesImpacted,
      modulesImpacted: data.modulesImpacted,
      riskLevel: data.riskLevel,
      currentStep: 3,
    }))
  }

  function completeStep3(storyId: string, storyTitle: string, storyPoints: number) {
    setState((prev) => ({ ...prev, storyId, storyTitle, storyPoints, currentStep: 4 }))
  }

  function completeStep4() {
    setState((prev) => ({ ...prev, currentStep: 5 }))
  }

  function reset() {
    setState(initialState)
  }

  return {
    state,
    setProjectId,
    setRequirementText,
    setLanguage,
    completeStep1,
    completeStep2,
    completeStep3,
    completeStep4,
    reset,
  }
}
