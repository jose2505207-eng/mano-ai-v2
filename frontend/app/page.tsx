"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { startTask, getTask, continueTask, approveTask, stopTask } from "@/lib/api";
import type { WebTaskRun } from "@/lib/types";
import ChatPanel from "@/components/ChatPanel";
import BrowserPanel from "@/components/BrowserPanel";
import RightPanel from "@/components/RightPanel";
import { Send, Mic, MicOff, Languages, Plane, Calendar, Search, FileText, Globe } from "lucide-react";

const EXAMPLES = [
  { text: "Book a flight from SFO to Guadalajara for June 20", icon: Plane },
  { text: "Schedule a DMV appointment in San Jose", icon: Calendar },
  { text: "Find the cheapest acupuncture clinic near me", icon: Search },
  { text: "Help me fill out this government form", icon: FileText },
  { text: "Translate this webpage to Spanish", icon: Globe },
];

export default function Home() {
  const [taskInput, setTaskInput] = useState("");
  const [currentTask, setCurrentTask] = useState<WebTaskRun | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [language, setLanguage] = useState<"en" | "es">("en");
  const [error, setError] = useState<string | null>(null);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recognitionRef = useRef<unknown>(null);
  const [voiceSupported, setVoiceSupported] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = typeof window !== "undefined"
      ? ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) as (new () => any) | undefined
      : undefined;
    setVoiceSupported(!!SR);
  }, []);

  const clearPoll = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  useEffect(() => () => clearPoll(), [clearPoll]);

  const startPoll = useCallback((taskId: string) => {
    clearPoll();
    pollIntervalRef.current = setInterval(async () => {
      try {
        const updated = await getTask(taskId);
        setCurrentTask(updated);
        if (["done", "stuck", "failed", "waiting_for_approval", "waiting_for_user"].includes(updated.status)) {
          clearPoll();
        }
      } catch {
        clearPoll();
      }
    }, 2000);
  }, [clearPoll]);

  const handleStartTask = useCallback(async (overrideTask?: string) => {
    const taskText = overrideTask ?? taskInput;
    if (!taskText.trim()) return;
    clearPoll();
    setError(null);
    try {
      const result = await startTask(taskText, language);
      setCurrentTask(result);
      startPoll(result.task_id);
      setTaskInput("");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    }
  }, [taskInput, language, clearPoll, startPoll]);

  const handleApprove = useCallback(async () => {
    if (!currentTask?.task_id) return;
    try {
      const result = await approveTask(currentTask.task_id);
      setCurrentTask(result);
      startPoll(result.task_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Approval failed");
    }
  }, [currentTask, startPoll]);

  const handleDeny = useCallback(async () => {
    if (!currentTask?.task_id) return;
    try {
      const result = await stopTask(currentTask.task_id);
      setCurrentTask(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Stop failed");
    }
  }, [currentTask]);

  const handleUserInput = useCallback(async (input: string) => {
    if (!currentTask?.task_id || !input.trim()) return;
    try {
      const result = await continueTask(currentTask.task_id, input);
      setCurrentTask(result);
      startPoll(result.task_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to send input");
    }
  }, [currentTask, startPoll]);

  const handleStop = useCallback(async () => {
    if (!currentTask?.task_id) return;
    clearPoll();
    try {
      const result = await stopTask(currentTask.task_id);
      setCurrentTask(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Stop failed");
    }
  }, [currentTask, clearPoll]);

  const handleVoiceInput = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SR = typeof window !== "undefined"
      ? ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) as (new () => any) | undefined
      : undefined;
    if (!SR) return;

    if (isRecording && recognitionRef.current) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (recognitionRef.current as any).stop();
      setIsRecording(false);
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const rec: any = new SR();
    rec.lang = language === "es" ? "es-US" : "en-US";
    rec.continuous = false;
    rec.interimResults = false;
    let transcript = "";

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    rec.onresult = (e: any) => {
      transcript = e.results[0][0].transcript;
    };
    rec.onend = () => {
      setIsRecording(false);
      if (transcript.trim()) {
        setTaskInput(transcript.trim());
        // Auto-submit if we have text and no task is running
        setTimeout(() => {
          if (transcript.trim() && !currentTask) {
            handleStartTask(transcript.trim());
          }
        }, 500);
      }
    };
    rec.onerror = () => {
      setIsRecording(false);
    };

    rec.start();
    recognitionRef.current = rec;
    setIsRecording(true);
  }, [isRecording, language]);

  const isActive = currentTask && ["running", "waiting_for_user", "waiting_for_approval"].includes(currentTask.status);
  const lastScreenshot = currentTask?.steps?.length
    ? [...currentTask.steps].reverse().find(s => s.result?.screenshot)?.result?.screenshot ?? null
    : null;

  return (
    <div className="flex flex-col h-screen">
      {/* Task Input Area */}
      <div className="border-b border-mano-border bg-mano-darker px-4 py-5 md:px-6">
        <div className="max-w-4xl mx-auto">
          {/* Hero text when no task */}
          {!currentTask && (
            <div className="text-center mb-6">
              <h1 className="text-2xl md:text-3xl font-bold text-mano-text mb-2">
                Mano AI
              </h1>
              <p className="text-mano-muted text-sm">
                The internet, guided step by step.
              </p>
            </div>
          )}

          {/* Input row */}
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                value={taskInput}
                onChange={(e) => setTaskInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleStartTask();
                  }
                }}
                placeholder="Tell Mano AI what you need done online..."
                rows={2}
                className="w-full bg-mano-surface border border-mano-border rounded-xl px-4 py-3 pr-20 text-mano-text placeholder-mano-muted resize-none focus:outline-none focus:border-mano-primary text-sm"
              />
              <div className="absolute right-2 bottom-2 flex items-center gap-1">
                {/* Language toggle */}
                <button
                  onClick={() => setLanguage(language === "en" ? "es" : "en")}
                  className="flex items-center gap-1 px-2 py-1 rounded-md bg-mano-darker hover:bg-mano-border/50 text-mano-muted hover:text-mano-text transition-colors text-xs"
                  title={`Switch to ${language === "en" ? "Spanish" : "English"}`}
                >
                  <Languages className="w-3.5 h-3.5" />
                  {language.toUpperCase()}
                </button>
                {/* Voice input */}
                {voiceSupported && (
                  <button
                    onClick={handleVoiceInput}
                    className={`p-1.5 rounded-md transition-colors ${
                      isRecording
                        ? "bg-red-500/20 text-red-400"
                        : "bg-mano-darker hover:bg-mano-border/50 text-mano-muted hover:text-mano-text"
                    }`}
                    title={isRecording ? "Stop recording" : "Voice input"}
                  >
                    {isRecording ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>
            </div>
            <button
              onClick={() => handleStartTask()}
              disabled={!!isActive || !taskInput.trim()}
              className="px-4 py-3 bg-mano-primary hover:bg-mano-primary/80 disabled:opacity-40 text-white rounded-xl transition-colors flex-shrink-0"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>

          {/* Error display */}
          {error && (
            <div className="mt-3 px-4 py-2 rounded-lg bg-red-900/20 border border-red-500/30 text-red-400 text-xs">
              {error}
            </div>
          )}

          {/* Example task cards */}
          {!currentTask && (
            <div className="mt-4 flex flex-wrap gap-2">
              {EXAMPLES.map(({ text, icon: Icon }) => (
                <button
                  key={text}
                  onClick={() => handleStartTask(text)}
                  className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg bg-mano-surface hover:bg-mano-surface/80 border border-mano-border/50 text-mano-muted hover:text-mano-text transition-colors"
                >
                  <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="truncate max-w-[200px]">{text}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Three-panel layout for active task */}
      {currentTask ? (
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          {/* ChatPanel - left */}
          <div className="w-full md:w-1/3 border-b md:border-b-0 md:border-r border-mano-border overflow-auto h-[33vh] md:h-auto">
            <ChatPanel steps={currentTask.steps} status={currentTask.status} />
          </div>
          {/* BrowserPanel - center */}
          <div className="flex-1 border-b md:border-b-0 md:border-r border-mano-border overflow-auto h-[33vh] md:h-auto">
            <BrowserPanel
              currentUrl={currentTask.current_url}
              screenshot={lastScreenshot}
              status={currentTask.status}
            />
          </div>
          {/* RightPanel - right */}
          <div className="w-full md:w-72 lg:w-80 overflow-auto h-[33vh] md:h-auto">
            <RightPanel
              task={currentTask}
              onApprove={handleApprove}
              onDeny={handleDeny}
              onUserInput={handleUserInput}
              onStop={handleStop}
            />
          </div>
        </div>
      ) : (
        /* Empty state */
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 rounded-2xl bg-mano-primary/10 flex items-center justify-center mx-auto mb-4">
              <Send className="w-8 h-8 text-mano-primary" />
            </div>
            <h2 className="text-lg font-semibold text-mano-text mb-2">
              Ready to help
            </h2>
            <p className="text-sm text-mano-muted">
              Describe any online task and Mano AI will navigate the web for you.
              From booking appointments to filling forms, just say what you need.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
