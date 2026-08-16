import {
  Box,
  Button,
  chakra,
  Flex,
  HStack,
  IconButton,
  SimpleGrid,
  Spacer,
  Stack,
  Text,
} from "@chakra-ui/react";
import {
  ArrowLeftOnRectangleIcon,
  ChartPieIcon,
  ClipboardDocumentListIcon,
  Cog6ToothIcon,
  DocumentMinusIcon,
  LinkIcon,
  SquaresPlusIcon,
  UserGroupIcon,
  UsersIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import { useDashboard } from "contexts/DashboardContext";
import useGetUser from "hooks/useGetUser";
import { FC, ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { fetch } from "service/http";
import { removeAuthToken } from "utils/authStorage";
import { BrandMark } from "./BrandMark";

const iconProps = { baseStyle: { w: 4, h: 4, flexShrink: 0 } };
const CoreSettingsIcon = chakra(Cog6ToothIcon, iconProps);
const LogoutIcon = chakra(ArrowLeftOnRectangleIcon, iconProps);
const HostsIcon = chakra(LinkIcon, iconProps);
const NodesIcon = chakra(SquaresPlusIcon, iconProps);
const NodesUsageIcon = chakra(ChartPieIcon, iconProps);
const ResetUsageIcon = chakra(DocumentMinusIcon, iconProps);
const UsersNavIcon = chakra(UsersIcon, iconProps);
const AdminsNavIcon = chakra(UserGroupIcon, iconProps);
const AuditNavIcon = chakra(ClipboardDocumentListIcon, iconProps);
const DeviceLimitNavIcon = chakra(ShieldCheckIcon, iconProps);

type ActionButtonProps = {
  icon: ReactElement;
  label: string;
  onClick: () => void;
  danger?: boolean;
};

const ActionButton: FC<ActionButtonProps> = ({ icon, label, onClick, danger }) => (
  <Button
    size="sm"
    variant="ghost"
    leftIcon={icon}
    justifyContent="flex-start"
    minW={0}
    w="full"
    color={danger ? "red.200" : "gray.200"}
    fontWeight="500"
    _hover={{ bg: danger ? "rgba(239, 68, 68, .14)" : "whiteAlpha.100", color: danger ? "red.100" : "white" }}
    _active={{ bg: danger ? "rgba(239, 68, 68, .2)" : "whiteAlpha.200" }}
    onClick={onClick}
  >
    <Text as="span" noOfLines={1}>{label}</Text>
  </Button>
);

export const Header: FC = () => {
  const { userData, getUserIsSuccess, getUserIsPending } = useGetUser();
  const isSudo = !getUserIsPending && getUserIsSuccess && userData.is_sudo;
  const { onEditingHosts, onResetAllUsage, onEditingNodes, onShowingNodesUsage } = useDashboard();
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const isAdminsPage = location.pathname.startsWith("/admins");
  const isAuditPage = location.pathname.startsWith("/audit-logs");
  const isDeviceLimitPage = location.pathname.startsWith("/device-limits");
  const isUsersPage = !isAdminsPage && !isAuditPage && !isDeviceLimitPage;
  const logout = async () => {
    try {
      await fetch("/admin/logout", { method: "POST" });
    } finally {
      removeAuthToken();
      navigate("/login/");
    }
  };
  return (
    <Flex
      as="aside"
      w={{ base: "full", lg: "272px" }}
      minW={{ lg: "272px" }}
      minH={{ lg: "100vh" }}
      h={{ lg: "100vh" }}
      position={{ base: "relative", lg: "sticky" }}
      top="0"
      zIndex="sticky"
      direction="column"
      bg="rgba(7, 19, 14, 0.97)"
      color="white"
      borderEndWidth={{ lg: "1px" }}
      borderBottomWidth={{ base: "1px", lg: "0" }}
      borderColor="rgba(91, 132, 108, 0.32)"
      backdropFilter="blur(16px)"
      px={{ base: 4, lg: 4 }}
      py={{ base: 3, lg: 5 }}
    >
      <HStack justify="space-between" align="center" gap={3}>
        <HStack spacing={3} minW={0}>
          <BrandMark aria-hidden="true" boxSize={{ base: "38px", lg: "46px" }} filter="drop-shadow(0 8px 20px rgba(34, 197, 94, 0.22))" />
          <Box minW={0}>
            <Text fontFamily="mono" fontSize="xs" fontWeight="700" letterSpacing="0.13em" color="primary.300" noOfLines={1}>HEISENBERG</Text>
            <Text fontSize="xs" color="gray.400" mt="1px" noOfLines={1}>Control laboratory</Text>
          </Box>
        </HStack>
        <HStack display={{ base: "flex", lg: "none" }} spacing={1} flexShrink={0}>
          <IconButton onClick={logout} size="sm" variant="ghost" color="red.200" aria-label={t("header.logout")} icon={<LogoutIcon />} />
        </HStack>
      </HStack>

      <Text display={{ base: "none", lg: "block" }} mt={8} mb={2} px={2} fontSize="xs" color="gray.500" fontFamily="mono" letterSpacing=".1em" textTransform="uppercase">Navigation</Text>
      <SimpleGrid as="nav" aria-label="Primary navigation" columns={{ base: isSudo ? 2 : 1, sm: isSudo ? 4 : 1, lg: 1 }} spacing={2} mt={{ base: 4, lg: 0 }}>
        <Button
          as={Link}
          to="/"
          size="md"
          variant={isUsersPage ? "solid" : "ghost"}
          colorScheme={isUsersPage ? "primary" : "gray"}
          color={isUsersPage ? "#07130e" : "gray.200"}
          _hover={isUsersPage ? undefined : { bg: "whiteAlpha.100", color: "white" }}
          leftIcon={<UsersNavIcon />}
          justifyContent="flex-start"
          aria-current={isUsersPage ? "page" : undefined}
        >{t("users")}</Button>
        {isSudo && (
          <Button
            as={Link}
            to="/admins/"
            size="md"
            variant={isAdminsPage ? "solid" : "ghost"}
            colorScheme={isAdminsPage ? "primary" : "gray"}
            color={isAdminsPage ? "#07130e" : "gray.200"}
            _hover={isAdminsPage ? undefined : { bg: "whiteAlpha.100", color: "white" }}
            leftIcon={<AdminsNavIcon />}
            justifyContent="flex-start"
            aria-current={isAdminsPage ? "page" : undefined}
          >{t("admins.nav")}</Button>
        )}
        {isSudo && (
          <Button
            as={Link}
            to="/device-limits/"
            size="md"
            variant={isDeviceLimitPage ? "solid" : "ghost"}
            colorScheme={isDeviceLimitPage ? "primary" : "gray"}
            color={isDeviceLimitPage ? "#07130e" : "gray.200"}
            _hover={isDeviceLimitPage ? undefined : { bg: "whiteAlpha.100", color: "white" }}
            leftIcon={<DeviceLimitNavIcon />}
            justifyContent="flex-start"
            aria-current={isDeviceLimitPage ? "page" : undefined}
          >{t("deviceLimit.nav")}</Button>
        )}
        {isSudo && (
          <Button
            as={Link}
            to="/audit-logs/"
            size="md"
            variant={isAuditPage ? "solid" : "ghost"}
            colorScheme={isAuditPage ? "cyan" : "gray"}
            color={isAuditPage ? "#06161a" : "gray.200"}
            _hover={isAuditPage ? undefined : { bg: "whiteAlpha.100", color: "white" }}
            leftIcon={<AuditNavIcon />}
            justifyContent="flex-start"
            aria-current={isAuditPage ? "page" : undefined}
          >{t("audit.nav")}</Button>
        )}
      </SimpleGrid>

      {isSudo && (
        <Box mt={{ base: 4, lg: 7 }} pt={{ base: 4, lg: 0 }} borderTopWidth={{ base: "1px", lg: "0" }} borderColor="whiteAlpha.200">
          <Text mb={2} px={2} fontSize="xs" color="gray.500" fontFamily="mono" letterSpacing=".1em" textTransform="uppercase">{t("core.configuration")}</Text>
          <SimpleGrid columns={{ base: 2, sm: 3, lg: 1 }} spacing={1}>
            <ActionButton icon={<CoreSettingsIcon />} label={t("core.title")} onClick={() => useDashboard.setState({ isEditingCore: true })} />
            <ActionButton icon={<HostsIcon />} label={t("header.hostSettings")} onClick={() => onEditingHosts(true)} />
            <ActionButton icon={<NodesIcon />} label={t("header.nodeSettings")} onClick={() => onEditingNodes(true)} />
            <ActionButton icon={<NodesUsageIcon />} label={t("header.nodesUsage")} onClick={() => onShowingNodesUsage(true)} />
            <ActionButton icon={<ResetUsageIcon />} label={t("resetAllUsage")} onClick={() => onResetAllUsage(true)} danger />
          </SimpleGrid>
        </Box>
      )}

      <Spacer display={{ base: "none", lg: "block" }} />
      <Stack display={{ base: "none", lg: "flex" }} mt={6} pt={4} borderTopWidth="1px" borderColor="whiteAlpha.200" spacing={2}>
        <Text fontSize="xs" color="gray.400" px={2} noOfLines={1}>{userData?.username || "Administrator"}</Text>
        <Button onClick={logout} size="sm" variant="ghost" color="red.200" leftIcon={<LogoutIcon />} justifyContent="flex-start" _hover={{ bg: "rgba(239, 68, 68, .14)", color: "red.100" }}>{t("header.logout")}</Button>
      </Stack>
    </Flex>
  );
};
