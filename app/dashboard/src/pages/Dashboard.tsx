import { Box, HStack, Text } from "@chakra-ui/react";
import { AppShell } from "components/AppShell";
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
import { useTranslation } from "react-i18next";
import { Statistics } from "../components/Statistics";

export const Dashboard: FC = () => {
  const { t } = useTranslation();
  useEffect(() => {
    useDashboard.getState().refetchUsers();
    fetchInbounds();
  }, []);
  return (
    <AppShell>
      <HStack justify="space-between" align="end" mb={6}>
        <Box>
          <Text color="primary.600" _dark={{ color: "primary.300" }} fontSize="xs" fontWeight="800" letterSpacing="0.13em" textTransform="uppercase">
            Control laboratory
          </Text>
          <Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" letterSpacing="-0.035em" mt={1}>
            {t("users")}
          </Text>
        </Box>
      </HStack>
      <Statistics />
      <Box mt={5} bg="white" _dark={{ bg: "surface.dark" }} borderWidth="1px" borderColor="gray.200" borderRadius="12px" boxShadow="panel" overflow="hidden">
        <Filters />
        <Box px={{ base: 3, md: 5 }} pb={5}>
          <UsersTable />
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
