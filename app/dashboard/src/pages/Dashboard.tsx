import { Box, HStack, Text } from "@chakra-ui/react";
import { AppShell } from "components/AppShell";
import { AdminCreditSummary } from "components/AdminCreditSummary";
import { DashboardOverview } from "components/DashboardOverview";
import { CoreSettingsModal } from "components/CoreSettingsModal";
import { DeleteUserModal } from "components/DeleteUserModal";
import { Filters } from "components/Filters";
import { HostsDialog } from "components/HostsDialog";
import { NodesDialog } from "components/NodesModal";
import { NodesUsage } from "components/NodesUsage";
import { QRCodeDialog } from "components/QRCodeDialog";
import { ResetAllUsageModal } from "components/ResetAllUsageModal";
import { ResetUserUsageModal } from "components/ResetUserUsageModal";
import { RevokeSubscriptionModal } from "components/RevokeSubscriptionModal";
import { UserDialog } from "components/UserDialog";
import { UsersTable } from "components/UsersTable";
import { fetchInbounds, useDashboard } from "contexts/DashboardContext";
import { FC, useEffect } from "react";
import { Statistics } from "../components/Statistics";

export const Dashboard: FC = () => {
  useEffect(() => {
    useDashboard.getState().refetchUsers();
    fetchInbounds();
  }, []);
  return (
    <AppShell>
      <HStack justify="space-between" align="end" mb={5}>
        <Box>
          <Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" letterSpacing="-0.035em">
            داشبورد
          </Text>
          <Text color="gray.400" mt={1}>آمار مهم حساب و کاربران را یکجا ببینید.</Text>
        </Box>
      </HStack>
      <AdminCreditSummary />
      <DashboardOverview />
      <Box as="section" aria-labelledby="system-health-title" mb={6}>
        <Text color="primary.300" fontSize="xs" fontWeight="800">وضعیت سرور</Text>
        <Text id="system-health-title" as="h2" mt={1} fontSize="lg" fontWeight="800">سلامت سرور</Text>
        <Text mt={1} mb={3} color="gray.400" fontSize="sm">تعداد کاربران فعال، ترافیک و حافظه مصرف‌شده.</Text>
        <Statistics />
      </Box>
      <Box as="section" aria-labelledby="user-operations-title">
        <Text color="primary.300" fontSize="xs" fontWeight="800">کاربران</Text>
        <Text id="user-operations-title" as="h2" mt={1} fontSize="lg" fontWeight="800">مدیریت کاربران</Text>
        <Text mt={1} color="gray.400" fontSize="sm">کاربر بسازید، جست‌وجو کنید یا فیلترها را تغییر دهید.</Text>
      <Box
        mt={3}
        w="full"
        minW={0}
        bg="rgba(3, 9, 17, .76)"
        borderWidth="1px"
        borderColor="rgba(148, 163, 184, .14)"
        borderRadius="14px"
        boxShadow="0 18px 48px rgba(0, 0, 0, .24)"
        backdropFilter="blur(18px)"
        overflow="hidden"
      >
        <Filters />
        <Box px={{ base: 3, md: 4, xl: 5 }} pb={5} minW={0}>
          <UsersTable />
        </Box>
      </Box>
      </Box>
        <UserDialog />
        <DeleteUserModal />
        <QRCodeDialog />
        <HostsDialog />
        <ResetUserUsageModal />
        <RevokeSubscriptionModal />
        <NodesDialog />
        <NodesUsage />
        <ResetAllUsageModal />
        <CoreSettingsModal />
    </AppShell>
  );
};

export default Dashboard;
