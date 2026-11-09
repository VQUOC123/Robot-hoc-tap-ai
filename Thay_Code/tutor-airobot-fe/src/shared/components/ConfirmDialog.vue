<script setup lang="ts">
import { useConfirm } from '@/shared/composables/useConfirm'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/shared/components/ui/alert-dialog'
import { cn } from '@/shared/utils'

const { isOpen, confirmOptions, onConfirm, onCancel } = useConfirm()
</script>

<template>
  <AlertDialog :open="isOpen" @update:open="(v) => !v && onCancel()">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>{{ confirmOptions.title }}</AlertDialogTitle>
        <AlertDialogDescription>{{ confirmOptions.description }}</AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel @click="onCancel">{{ confirmOptions.cancelText }}</AlertDialogCancel>
        <AlertDialogAction
          :class="
            cn(
              confirmOptions.variant === 'destructive' &&
                'bg-destructive text-destructive-foreground hover:bg-destructive/90',
            )
          "
          @click="onConfirm"
        >
          {{ confirmOptions.confirmText }}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
