import { Title, Text, Stack } from '@mantine/core'
import { config } from '@/config'

export const HomePage = () => (
  <Stack className="p-8">
    <Title order={1}>{config.appName}</Title>
    <Text c="dimmed">
      Edit <code>src/features/home/HomePage.tsx</code> to get started.
    </Text>
  </Stack>
)
