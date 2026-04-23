'use client';

import { useState, useEffect } from 'react';
import { ImageIcon } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useNotifications } from '@/components/ui/notifications';
import { AvatarDisplay } from '@/components/ui/avatar-display';
import { useUser } from '@/lib/auth';
import { useDisclosure } from '@/hooks/use-disclosure';
import {
  Drawer,
  DrawerTrigger,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerFooter,
  DrawerClose,
} from '@/components/ui/drawer';

import {
  updateAvatarInputSchema,
  useUpdateAvatar,
} from '../api/update-avatar';

const AVATAR_LIST = [
  'Alligator', 'Anteater', 'Armadillo', 'Auroch', 'Axolotl', 'Badger', 'Bat', 'Beaver',
  'Buffalo', 'Camel', 'Capybara', 'Chameleon', 'Cheetah', 'Chinchilla', 'Chipmunk',
  'Chupacabra', 'Cormorant', 'Coyote', 'Crow', 'Dingo', 'Dinosaur', 'Dolphin', 'Duck',
  'Elephant', 'Ferret', 'Fox', 'Frog', 'Giraffe', 'Gopher', 'Grizzly', 'Hedgehog',
  'Hippo', 'Hyena', 'Ibex', 'Ifrit', 'Iguana', 'Jackal', 'Kangaroo', 'Koala',
  'Kraken', 'Lemur', 'Leopard', 'Liger', 'Llama', 'Manatee', 'Mink', 'Monkey',
  'Moose', 'Narwhal', 'Orangutan', 'Otter', 'Panda', 'Penguin', 'Platypus', 'Pumpkin',
  'Python', 'Quagga', 'Rabbit', 'Raccoon', 'Rhino', 'Sheep', 'Shrew', 'Skunk',
  'Squirrel', 'Tiger', 'Turtle', 'Walrus', 'Wolf', 'Wolverine', 'Wombat'
];

const COLOR_PRESETS = [
  '#38bdf8', // cyan
  '#ef4444', // red
  '#f97316', // orange
  '#eab308', // yellow
  '#22c55e', // green
  '#06b6d4', // cyan-2
  '#3b82f6', // blue
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#64748b', // slate
];

export const UpdateAvatar = () => {
  const user = useUser();
  const { addNotification } = useNotifications();
  const { open, close, isOpen } = useDisclosure();
  
  const userAvatar = user.data?.avatar_name || 'Dinosaur';
  const userColor = user.data?.avatar_color || '#38bdf8';
  
  const [selectedAvatar, setSelectedAvatar] = useState(userAvatar);
  const [selectedColor, setSelectedColor] = useState(userColor);
  const [customColor, setCustomColor] = useState(userColor);
  const [useCustomColor, setUseCustomColor] = useState(!COLOR_PRESETS.includes(userColor));

  // Update local state when user data changes
  useEffect(() => {
    setSelectedAvatar(userAvatar);
    setSelectedColor(userColor);
    setCustomColor(userColor);
    setUseCustomColor(!COLOR_PRESETS.includes(userColor));
  }, [userAvatar, userColor]);

  const updateAvatarMutation = useUpdateAvatar({
    mutationConfig: {
      onSuccess: () => {
        addNotification({
          type: 'success',
          title: 'Avatar Updated',
          message: 'Your avatar has been updated successfully.',
        });
        close();
      },
      onError: () => {
        addNotification({
          type: 'error',
          title: 'Update Failed',
          message: 'Could not update your avatar. Please try again.',
        });
      },
    },
  });

  const handleSaveAvatar = (e: React.FormEvent) => {
    e.preventDefault();
    const finalColor = useCustomColor ? customColor : selectedColor;
    
    // Validate before submitting
    try {
      updateAvatarInputSchema.parse({
        avatar_name: selectedAvatar,
        avatar_color: finalColor,
      });
    } catch (e: any) {
      addNotification({
        type: 'error',
        title: 'Validation Error',
        message: e.errors?.[0]?.message || 'Invalid avatar or color',
      });
      return;
    }
    
    updateAvatarMutation.mutate({
      data: {
        avatar_name: selectedAvatar,
        avatar_color: finalColor,
      },
    });
  };

  return (
    <Drawer open={isOpen} onOpenChange={(newOpen) => {
      if (newOpen) open();
      else close();
    }}>
      <DrawerTrigger asChild>
        <Button icon={<ImageIcon className="size-4" />} size="sm">
          Change Avatar
        </Button>
      </DrawerTrigger>
      <DrawerContent className="flex max-w-[800px] flex-col justify-between sm:max-w-[540px]">
        <form onSubmit={handleSaveAvatar} className="flex flex-col">
          <DrawerHeader>
            <DrawerTitle>Change Your Avatar</DrawerTitle>
          </DrawerHeader>
          <div className="space-y-4 px-6">
            {/* Preview */}
            <div className="rounded-lg border border-border bg-secondary/50 p-4 flex items-center gap-4">
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2">Preview</p>
                <AvatarDisplay
                  avatarName={selectedAvatar}
                  avatarColor={useCustomColor ? customColor : selectedColor}
                  size="lg"
                />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">{selectedAvatar}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Color: {useCustomColor ? customColor : selectedColor}
                </p>
              </div>
            </div>

            {/* Avatar Selection */}
            <div>
              <label className="text-sm font-semibold text-foreground mb-2 block">
                Choose Animal
              </label>
              <div className="max-h-48 overflow-y-auto rounded-lg border border-border bg-secondary/50 p-3">
                <div className="grid grid-cols-5 gap-2">
                  {AVATAR_LIST.map((avatar) => (
                    <button
                      key={avatar}
                      type="button"
                      onClick={() => setSelectedAvatar(avatar)}
                      className={`aspect-square rounded-lg overflow-hidden border-2 transition-all ${
                        selectedAvatar === avatar
                          ? 'border-blue-500 ring-2 ring-blue-400'
                          : 'border-border hover:border-foreground/30'
                      }`}
                      title={avatar}
                    >
                      <img
                        src={`/avatars/${avatar}.png`}
                        alt={avatar}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Color Selection */}
            <div>
              <label className="text-sm font-semibold text-foreground mb-2 block">
                Choose Color
              </label>
              <div className="space-y-3">
                <div className="flex gap-2 flex-wrap">
                  {COLOR_PRESETS.map((color) => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => {
                        setSelectedColor(color);
                        setUseCustomColor(false);
                      }}
                      className={`w-10 h-10 rounded-lg border-2 transition-all ${
                        !useCustomColor && selectedColor === color
                          ? 'border-foreground ring-2 ring-foreground/30'
                          : 'border-border hover:border-foreground/30'
                      }`}
                      style={{ backgroundColor: color }}
                      title={color}
                    />
                  ))}
                </div>

                {/* Custom Color Input */}
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={customColor}
                    onChange={(e) => {
                      setCustomColor(e.target.value);
                      setUseCustomColor(true);
                    }}
                    className="w-10 h-10 rounded-lg cursor-pointer border border-border"
                  />
                  <input
                    type="text"
                    value={customColor}
                    onChange={(e) => {
                      if (/^#[0-9A-F]{6}$/i.test(e.target.value)) {
                        setCustomColor(e.target.value);
                        setUseCustomColor(true);
                      }
                    }}
                    placeholder="#000000"
                    className="flex-1 px-3 py-2 rounded-lg border border-border bg-card text-sm text-foreground"
                  />
                </div>
              </div>
            </div>
          </div>
          <DrawerFooter>
            <DrawerClose asChild>
              <Button variant="outline" type="button">
                Close
              </Button>
            </DrawerClose>
            <Button
              type="submit"
              size="sm"
              isLoading={updateAvatarMutation.isPending}
            >
              Save Avatar
            </Button>
          </DrawerFooter>
        </form>
      </DrawerContent>
    </Drawer>
  );
};
