"use client"

import { useState } from "react"

export type WorkflowState = {
  sourceConnectionId: string | null
  repoFullName: string | null
  projectId: string
  ticketProjectKey: string
  requirementText: string
  language: string
  requirementId: string | null
  intent: string | null
  featureType: string | null
  complexity: string | null
  keywords: string[]
  evaluatedByModel: string | null
  coherenceModel: string | null
  coherenceCalls: number
  parserModel: string | null
  parserCalls: number
  generatorModel: string | null
  generatorCalls: number
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
  sourceConnectionId: null,
  repoFullName: null,
  projectId: "my-project",
  ticketProjectKey: "",
  requirementText: "",
  language: "es",
  requirementId: null,
  intent: null,
  featureType: null,
  complexity: null,
  keywords: [],
  evaluatedByModel: null,
  coherenceModel: null,
  coherenceCalls: 0,
  parserModel: null,
  parserCalls: 0,
  generatorModel: null,
  generatorCalls: 0,
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

  function setTicketProjectKey(ticketProjectKey: string) {
    setState((prev) => ({ ...prev, ticketProjectKey }))
  }

  function setRequirementText(requirementText: string) {
    setState((prev) => ({ ...prev, requirementText }))
  }

  function setLanguage(language: string) {
    setState((prev) => ({ ...prev, language }))
  }

  function syncSourceConnection(nextId: string | null, nextRepo: string | null = null) {
    setState((prev) => {
      if (prev.sourceConnectionId === nextId && prev.repoFullName === nextRepo) return prev
      // Reset everything when the connection OR the selected repo changes to avoid
      // mixing requirement/analysis/story data from different codebases.
      return { ...initialState, sourceConnectionId: nextId, repoFullName: nextRepo, language: prev.language }
    })
  }

  function completeStep1(data: {
    requirementId: string
    intent: string
    featureType: string
    complexity: string
    keywords: string[]
    evaluatedByModel: string | null
    coherenceModel: string | null
    coherenceCalls: number
    parserModel: string | null
    parserCalls: number
  }) {
    setState((prev) => ({
      ...prev,
      requirementId: data.requirementId,
      intent: data.intent,
      featureType: data.featureType,
      complexity: data.complexity,
      keywords: data.keywords,
      evaluatedByModel: data.evaluatedByModel,
      coherenceModel: data.coherenceModel,
      coherenceCalls: data.coherenceCalls,
      parserModel: data.parserModel,
      parserCalls: data.parserCalls,
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

  function setGeneratorInfo(generatorModel: string | null, generatorCalls: number) {
    setState((prev) => ({ ...prev, generatorModel, generatorCalls }))
  }

  function completeStep4() {
    setState((prev) => ({ ...prev, currentStep: 5 }))
  }

  function reset() {
    setState((prev) => ({ ...initialState, sourceConnectionId: prev.sourceConnectionId, repoFullName: prev.repoFullName }))
  }

  function goBackToStep1() {
    setState((prev) => ({
      ...prev,
      requirementId: null,
      intent: null,
      featureType: null,
      complexity: null,
      keywords: [],
      evaluatedByModel: null,
      coherenceModel: null,
      coherenceCalls: 0,
      parserModel: null,
      parserCalls: 0,
      generatorModel: null,
      generatorCalls: 0,
      analysisId: null,
      filesImpacted: null,
      modulesImpacted: [],
      riskLevel: null,
      storyId: null,
      storyTitle: null,
      storyPoints: null,
      currentStep: 1,
    }))
  }

  return {
    state,
    setProjectId,
    setTicketProjectKey,
    setRequirementText,
    setLanguage,
    syncSourceConnection,
    completeStep1,
    completeStep2,
    completeStep3,
    completeStep4,
    setGeneratorInfo,
    reset,
    goBackToStep1,
  }
}
