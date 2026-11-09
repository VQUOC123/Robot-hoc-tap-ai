import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'

export const promptSchema = z.object({
  name: z.string().min(1, 'Tên không được trống').max(100),
  description: z.string().max(500).optional(),
  content: z.string().min(10, 'Nội dung prompt quá ngắn'),
  is_default: z.boolean().default(false),
})

export const promptVeeSchema = toTypedSchema(promptSchema)
export type PromptFormValues = z.infer<typeof promptSchema>
