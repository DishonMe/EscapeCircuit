'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useUser } from '@/lib/auth';
import { Sparkles } from 'lucide-react';

const ALL_TUTORIALS = ['browse-puzzles', 'solving-page', 'arsenal', 'my-puzzles', 'arsenal-creator', 'create-puzzle', 'debugger'];

/**
 * Get list of tutorials that haven't been completed yet
 */
function getRemainingTutorials(tutorialsCompletedStr: string): string[] {
  const completed = tutorialsCompletedStr
    .split(',')
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
  return ALL_TUTORIALS.filter((t) => !completed.includes(t));
}

/**
 * Displays a tutorial suggestion modal when a user logs in or registers
 * if they haven't completed all tutorials yet.
 */
export const TutorialSuggestionHandler = () => {
  const { data: user, isLoading } = useUser();
  const router = useRouter();
  const hasShownRef = useRef(false);
  const lastUserIdRef = useRef<string | null>(null);
  const [showSuggestion, setShowSuggestion] = useState(false);

  useEffect(() => {
    // Don't process if user is loading
    if (isLoading) {
      console.log('[TutorialSuggestionHandler] User is loading...');
      return;
    }

    if (user) {
      console.log('[TutorialSuggestionHandler] User data:', { id: user.id, tutorials_completed: user.tutorials_completed });
      
      // Reset flag if user changed (logged out then back in, or different account)
      if (lastUserIdRef.current !== user.id) {
        console.log('[TutorialSuggestionHandler] User changed! Resetting hasShownRef', { from: lastUserIdRef.current, to: user.id });
        hasShownRef.current = false;
        lastUserIdRef.current = user.id;
      }
      
      const remaining = getRemainingTutorials(user.tutorials_completed);
      const hasCompletedAny = user.tutorials_completed && user.tutorials_completed.trim().length > 0;
      console.log('[TutorialSuggestionHandler] User tutorials_completed:', user.tutorials_completed, 'hasCompletedAny:', hasCompletedAny, 'hasShownRef:', hasShownRef.current);
      
      // Show modal only if user hasn't completed ANY tutorials yet
      if (!hasCompletedAny && !hasShownRef.current) {
        console.log('[TutorialSuggestionHandler] Showing modal (user has no tutorials completed)');
        hasShownRef.current = true;
        setShowSuggestion(true);
      }
      
      // If user has completed at least one tutorial, close the modal and don't show again this session
      if (hasCompletedAny && hasShownRef.current) {
        console.log('[TutorialSuggestionHandler] Closing modal (user completed a tutorial)');
        setShowSuggestion(false);
        hasShownRef.current = false;
      }
    } else {
      console.log('[TutorialSuggestionHandler] No user (logged out)');
    }
  }, [user, isLoading]);

  const handleStartTutorial = useCallback(() => {
    setShowSuggestion(false);
    const remaining = getRemainingTutorials(user?.tutorials_completed || '');
    
    // Determine which tutorial page to redirect to
    let targetPath = '/app/puzzles'; // Default to browse-puzzles
    if (remaining.length > 0) {
      const nextTutorial = remaining[0];
      console.log('[TutorialSuggestionHandler] Starting next tutorial:', nextTutorial);
      
      if (nextTutorial === 'browse-puzzles') {
        targetPath = '/app/puzzles?startTutorial=true';
      } else if (nextTutorial === 'arsenal') {
        targetPath = '/app/arsenal?startTutorial=true';
      } else if (nextTutorial === 'my-puzzles') {
        targetPath = '/app/my-puzzles?startTutorial=true';
      } else if (nextTutorial === 'arsenal-creator') {
        targetPath = '/app/arsenal/creator?startTutorial=true';
      } else if (nextTutorial === 'create-puzzle') {
        targetPath = '/app/create-puzzle?startTutorial=true';
      }
    } else {
      targetPath = '/app/puzzles?startTutorial=true';
    }
    
    router.push(targetPath);
  }, [user, router]);

  const handleDismiss = useCallback(() => {
    setShowSuggestion(false);
  }, []);

  return (
    <Dialog open={showSuggestion} onOpenChange={setShowSuggestion}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="size-5 text-amber-500" />
            Complete a Tutorial
          </DialogTitle>
          <DialogDescription>
            New to Circuit Puzzles? Complete a tutorial to earn 10 XP and learn how to solve puzzles!
          </DialogDescription>
        </DialogHeader>

        <DialogFooter className="gap-2 sm:justify-end">
          <Button
            type="button"
            variant="ghost"
            onClick={handleDismiss}
          >
            Not now
          </Button>
          <Button type="button" onClick={handleStartTutorial}>
            Start tutorial
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
