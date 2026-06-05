import { Outlet } from '@tanstack/react-router'
import { AppShell } from '@mantine/core'

export const RootLayout = () => (
  <AppShell padding="md">
    <AppShell.Main>
      <Outlet />
    </AppShell.Main>
  </AppShell>
)
