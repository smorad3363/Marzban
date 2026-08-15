import {
  Badge,
  Box,
  BoxProps,
  Button,
  Card,
  chakra,
  Checkbox,
  Collapse,
  Divider,
  Flex,
  HStack,
  IconButton,
  Popover,
  PopoverArrow,
  PopoverBody,
  PopoverCloseButton,
  PopoverContent,
  PopoverHeader,
  PopoverTrigger,
  Portal,
  SimpleGrid,
  Stack,
  Text,
  Tooltip,
  usePrefersReducedMotion,
  VStack,
} from "@chakra-ui/react";
import {
  ArrowPathIcon,
  CalendarDaysIcon,
  CheckIcon,
  ChevronDownIcon,
  ClipboardIcon,
  DevicePhoneMobileIcon,
  LinkIcon,
  PencilIcon,
  QrCodeIcon,
  RectangleStackIcon,
  UserCircleIcon,
} from "@heroicons/react/24/outline";
import { ReactComponent as AddFileIcon } from "assets/add_file.svg";
import { resetStrategy, statusColors } from "constants/UserSettings";
import { useDashboard } from "contexts/DashboardContext";
import { FC, ReactNode, useEffect, useState } from "react";
import CopyToClipboard from "react-copy-to-clipboard";
import { useTranslation } from "react-i18next";
import { User } from "types/User";
import { formatBytes } from "utils/formatByte";
import { OnlineBadge } from "./OnlineBadge";
import { Pagination } from "./Pagination";
import { BulkUserActions } from "./BulkUserActions";

const EmptySectionIcon = chakra(AddFileIcon);
const iconProps = { baseStyle: { w: 4, h: 4 } };
const CopyIcon = chakra(ClipboardIcon, iconProps);
const CopiedIcon = chakra(CheckIcon, iconProps);
const SubscriptionLinkIcon = chakra(LinkIcon, iconProps);
const QRIcon = chakra(QrCodeIcon, iconProps);
const EditIcon = chakra(PencilIcon, iconProps);
const ExpirationIcon = chakra(CalendarDaysIcon, iconProps);
const AccountIcon = chakra(UserCircleIcon, iconProps);
const SubscriptionIcon = chakra(ArrowPathIcon, iconProps);
const DeviceIcon = chakra(DevicePhoneMobileIcon, iconProps);
const PlanIcon = chakra(RectangleStackIcon, iconProps);
const DetailsIcon = chakra(ChevronDownIcon, { baseStyle: { w: 4, h: 4 } });

type UsagePanelProps = {
  used: number;
  total: number | null;
  dataLimitResetStrategy: string | null;
  totalUsedTraffic: number;
};

const getResetStrategy = (strategy: string): string => {
  const entry = resetStrategy.find((item) => item.value === strategy);
  return entry?.title || "No";
};

const UsagePanel: FC<UsagePanelProps> = ({
  used,
  total,
  dataLimitResetStrategy,
  totalUsedTraffic,
}) => {
  const { t, i18n } = useTranslation();
  const reduceMotion = usePrefersReducedMotion();
  const direction = i18n.dir();
  const isUnlimited = total === 0 || total === null;
  const percent = isUnlimited
    ? 100
    : Math.min((used / Math.max(total, 1)) * 100, 100);
  const isReached = !isUnlimited && percent >= 100;
  const remaining = isUnlimited ? null : Math.max((total || 0) - used, 0);
  const limitText = isUnlimited
    ? "∞"
    : formatBytes(total) +
      (dataLimitResetStrategy && dataLimitResetStrategy !== "no_reset"
        ? ` ${t(
            `userDialog.resetStrategy${getResetStrategy(
              dataLimitResetStrategy
            )}`
          )}`
        : "");
  const resetText = t(
    `userDialog.resetStrategy${getResetStrategy(
      dataLimitResetStrategy || "no_reset"
    )}`
  );

  return (
    <Box
      dir={direction}
      minW={0}
      p={3}
      borderRadius="12px"
      bg="rgba(2, 6, 23, .48)"
      borderWidth="1px"
      borderColor="rgba(148, 163, 184, .14)"
    >
      <HStack justify="space-between" align="center" gap={3} minW={0}>
        <Stack spacing={0.5} minW={0}>
          <MetaLabel>{t("usersTable.dataUsage")}</MetaLabel>
          <Text
            dir="ltr"
            textAlign="start"
            fontSize={{ base: "md", md: "sm" }}
            fontFamily="mono"
            fontWeight="700"
            color="gray.100"
            noOfLines={1}
            sx={{ unicodeBidi: "isolate" }}
          >
            {formatBytes(used)} / {limitText}
          </Text>
        </Stack>
        <Box
          flexShrink={0}
          px={2.5}
          py={1}
          borderRadius="full"
          bg={
            isReached ? "rgba(248, 113, 113, .12)" : "rgba(45, 212, 191, .08)"
          }
          borderWidth="1px"
          borderColor={
            isReached ? "rgba(248, 113, 113, .28)" : "rgba(45, 212, 191, .2)"
          }
        >
          <Text
            dir="ltr"
            fontFamily="mono"
            fontSize="xs"
            fontWeight="800"
            color={isReached ? "red.300" : "teal.200"}
          >
            {isUnlimited ? "∞" : `${Math.round(percent)}%`}
          </Text>
        </Box>
      </HStack>

      <Box
        role="progressbar"
        aria-label={`${formatBytes(used)} / ${limitText}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={isUnlimited ? undefined : Math.round(percent)}
        mt={3}
        h="7px"
        w="full"
        overflow="hidden"
        borderRadius="full"
        bg="rgba(148, 163, 184, 0.13)"
      >
        <Box
          h="full"
          w={`${percent}%`}
          minW={percent > 0 ? "7px" : 0}
          borderRadius="full"
          bgGradient={
            isReached
              ? "linear(to-r, red.500, red.300)"
              : "linear(to-r, teal.600, cyan.300)"
          }
          boxShadow={
            isReached
              ? "0 0 10px rgba(248,113,113,.24)"
              : "0 0 10px rgba(45,212,191,.2)"
          }
          transition={reduceMotion ? "none" : "width 260ms ease"}
        />
      </Box>

      <Flex
        mt={2.5}
        gap={2}
        justify="space-between"
        align="center"
        wrap="wrap"
        minW={0}
      >
        <HStack spacing={2.5} flexWrap="wrap">
          {remaining !== null && (
            <Text color="gray.400" fontSize="xs" noOfLines={1}>
              {t("usersTable.remaining")}:{" "}
              <Text
                as="span"
                dir="ltr"
                display="inline-block"
                fontFamily="mono"
                color="teal.200"
                sx={{ unicodeBidi: "isolate" }}
              >
                {formatBytes(remaining)}
              </Text>
            </Text>
          )}
          <Text color="gray.400" fontSize="xs" noOfLines={1}>
            {t("usersTable.total")}:{" "}
            <Text
              as="span"
              dir="ltr"
              display="inline-block"
              fontFamily="mono"
              color="gray.300"
              sx={{ unicodeBidi: "isolate" }}
            >
              {formatBytes(totalUsedTraffic)}
            </Text>
          </Text>
        </HStack>
        <Badge
          variant="subtle"
          bg="whiteAlpha.50"
          color="gray.300"
          borderRadius="full"
          px={2}
          py={0.5}
          textTransform="none"
          fontSize={{ base: "sm", md: "xs" }}
          whiteSpace="nowrap"
        >
          {t("usersTable.resetCycle")}: {resetText}
        </Badge>
      </Flex>
    </Box>
  );
};

const formatDateTime = (value: string | null | undefined, locale: string) => {
  if (!value) return "—";
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value)
    ? value
    : `${value}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

const formatTimestamp = (value: number | null | undefined, locale: string) => {
  if (!value) return "—";
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
    new Date(value * 1000)
  );
};

const MetaLabel: FC<{ children: ReactNode }> = ({ children }) => (
  <Text color="gray.400" fontSize="xs" fontWeight="600" lineHeight="1.6">
    {children}
  </Text>
);

type DetailSectionProps = {
  title: ReactNode;
  icon: ReactNode;
  children: ReactNode;
};

const DetailSection: FC<DetailSectionProps> = ({ title, icon, children }) => (
  <Box
    minW={0}
    p={{ base: 3.5, md: 4 }}
    borderRadius="12px"
    bg="rgba(15, 23, 42, .58)"
    backdropFilter="blur(14px)"
    borderWidth="1px"
    borderColor="rgba(148, 163, 184, .16)"
    boxShadow="inset 0 1px 0 rgba(255,255,255,.025)"
  >
    <HStack spacing={2.5} mb={3} minW={0}>
      <Flex
        boxSize="32px"
        flexShrink={0}
        align="center"
        justify="center"
        borderRadius="9px"
        color="teal.200"
        bg="rgba(45, 212, 191, .09)"
        borderWidth="1px"
        borderColor="rgba(45, 212, 191, .16)"
        aria-hidden="true"
      >
        {icon}
      </Flex>
      <Text
        color="gray.100"
        fontSize="sm"
        fontWeight="800"
        lineHeight="1.6"
        noOfLines={1}
      >
        {title}
      </Text>
    </HStack>
    {children}
  </Box>
);

const DetailItem: FC<{
  label: ReactNode;
  children: ReactNode;
  icon?: ReactNode;
}> = ({ label, children, icon }) => (
  <Box minW={0}>
    <HStack spacing={1.5} color="gray.400" minW={0}>
      {icon && (
        <Box display="inline-flex" flexShrink={0} aria-hidden="true">
          {icon}
        </Box>
      )}
      <MetaLabel>{label}</MetaLabel>
    </HStack>
    <Box mt={1.5} minW={0} color="gray.200">
      {children}
    </Box>
  </Box>
);

const statusPalette: Record<
  User["status"],
  {
    background: string;
    border: string;
    color: string;
    halo: string;
  }
> = {
  active: {
    background: "rgba(34, 197, 94, .12)",
    border: "rgba(74, 222, 128, .34)",
    color: "green.200",
    halo: "rgba(34, 197, 94, .16)",
  },
  connected: {
    background: "rgba(34, 197, 94, .12)",
    border: "rgba(74, 222, 128, .34)",
    color: "green.200",
    halo: "rgba(34, 197, 94, .16)",
  },
  connecting: {
    background: "rgba(245, 158, 11, .12)",
    border: "rgba(251, 191, 36, .36)",
    color: "orange.200",
    halo: "rgba(245, 158, 11, .16)",
  },
  on_hold: {
    background: "rgba(245, 158, 11, .12)",
    border: "rgba(251, 191, 36, .36)",
    color: "orange.200",
    halo: "rgba(245, 158, 11, .16)",
  },
  disabled: {
    background: "rgba(239, 68, 68, .12)",
    border: "rgba(248, 113, 113, .34)",
    color: "red.200",
    halo: "rgba(239, 68, 68, .16)",
  },
  expired: {
    background: "rgba(239, 68, 68, .12)",
    border: "rgba(248, 113, 113, .34)",
    color: "red.200",
    halo: "rgba(239, 68, 68, .16)",
  },
  limited: {
    background: "rgba(239, 68, 68, .12)",
    border: "rgba(248, 113, 113, .34)",
    color: "red.200",
    halo: "rgba(239, 68, 68, .16)",
  },
  error: {
    background: "rgba(239, 68, 68, .12)",
    border: "rgba(248, 113, 113, .34)",
    color: "red.200",
    halo: "rgba(239, 68, 68, .16)",
  },
};

const GlowStatusBadge: FC<{ user: User }> = ({ user }) => {
  const { t } = useTranslation();
  const visual = statusPalette[user.status];
  const StatusIcon = statusColors[user.status].icon;

  return (
    <Badge
      display="inline-flex"
      alignItems="center"
      gap={1.5}
      flexShrink={0}
      px={2.5}
      py={1.5}
      borderRadius="full"
      bg={visual.background}
      borderWidth="1px"
      borderColor={visual.border}
      color={visual.color}
      textTransform="none"
      whiteSpace="nowrap"
      boxShadow={`0 0 12px ${visual.halo}`}
    >
      <StatusIcon w={3.5} h={3.5} aria-hidden="true" />
      <Text as="span" fontSize="xs" fontWeight="800" lineHeight="1">
        {t(`status.${user.status}`)}
      </Text>
    </Badge>
  );
};

type UserIdentityProps = {
  user: User;
  owner: string;
  selected: boolean;
  onSelectedChange: (selected: boolean) => void;
};

const UserIdentity: FC<UserIdentityProps> = ({
  user,
  owner,
  selected,
  onSelectedChange,
}) => {
  const { t, i18n } = useTranslation();

  return (
    <HStack
      dir={i18n.dir()}
      justify="space-between"
      align="start"
      gap={3}
      minW={0}
    >
      <Box minW={0} flex="1">
        <HStack spacing={2} minW={0}>
          <OnlineBadge lastOnline={user.online_at} />
          <Text
            dir="ltr"
            textAlign="start"
            fontFamily="mono"
            fontSize={{ base: "md", md: "lg" }}
            fontWeight="800"
            letterSpacing="-.015em"
            color="gray.50"
            noOfLines={1}
            minW={0}
            sx={{ unicodeBidi: "isolate" }}
          >
            {user.username}
          </Text>
        </HStack>
        <HStack mt={1.5} spacing={1.5} minW={0} flexWrap="wrap">
          <Badge
            maxW="full"
            overflow="hidden"
            textOverflow="ellipsis"
            whiteSpace="nowrap"
            px={2}
            py={0.5}
            borderRadius="full"
            bg="whiteAlpha.50"
            color="gray.400"
            borderWidth="1px"
            borderColor="whiteAlpha.100"
            textTransform="none"
            fontSize="xs"
            fontWeight="600"
          >
            {t("usersTable.admin")}:{" "}
            <Text
              as="span"
              dir="ltr"
              color="teal.200"
              sx={{ unicodeBidi: "isolate" }}
            >
              {owner}
            </Text>
          </Badge>
        </HStack>
      </Box>
      <Stack align="flex-end" spacing={2} flexShrink={0}>
        <Checkbox
          isChecked={selected}
          onChange={(event) => onSelectedChange(event.target.checked)}
          colorScheme="teal"
          size="lg"
          aria-label={`${t("usersTable.selectUser")}: ${user.username}`}
        />
        <GlowStatusBadge user={user} />
      </Stack>
    </HStack>
  );
};

const ExpirationMeta: FC<{ user: User }> = ({ user }) => {
  const { t, i18n } = useTranslation();
  const hasExpiration = Boolean(user.expire);
  const remainingTime = user.expire ? user.expire * 1000 - Date.now() : null;
  const expirationState =
    remainingTime === null
      ? null
      : remainingTime >= 0
      ? t("usersTable.daysRemaining", {
          count: Math.max(1, Math.ceil(remainingTime / 86400000)),
        })
      : Math.floor(Math.abs(remainingTime) / 86400000) === 0
      ? t("usersTable.expiredToday")
      : t("usersTable.expiredDaysAgo", {
          count: Math.floor(Math.abs(remainingTime) / 86400000),
        });
  const isExpired = remainingTime !== null && remainingTime < 0;

  return (
    <HStack
      minW={0}
      spacing={2}
      px={3}
      py={2.5}
      borderRadius="12px"
      bg="rgba(2, 6, 23, .42)"
      borderWidth="1px"
      borderColor="rgba(148, 163, 184, .14)"
    >
      <Flex
        boxSize="30px"
        flexShrink={0}
        align="center"
        justify="center"
        borderRadius="9px"
        bg="rgba(45, 212, 191, .1)"
        color="teal.200"
      >
        <ExpirationIcon aria-hidden="true" />
      </Flex>
      <Box minW={0} flex="1">
        <MetaLabel>{t("usersTable.expiration")}</MetaLabel>
        <Text
          mt={0.5}
          dir={hasExpiration ? "ltr" : i18n.dir()}
          textAlign="start"
          fontSize={{ base: "md", md: "sm" }}
          fontFamily={hasExpiration ? "mono" : "body"}
          color={hasExpiration ? "gray.200" : "teal.200"}
          noOfLines={1}
          sx={{ unicodeBidi: "isolate" }}
        >
          {hasExpiration
            ? formatTimestamp(user.expire, i18n.language)
            : t("unlimited")}
        </Text>
        {expirationState && (
          <Text
            mt={1}
            fontSize="sm"
            fontWeight="700"
            color={isExpired ? "red.300" : "teal.200"}
          >
            {expirationState}
          </Text>
        )}
      </Box>
    </HStack>
  );
};

const NextPlanSummary: FC<{ user: User }> = ({ user }) => {
  const { t, i18n } = useTranslation();
  const plan = user.next_plan;
  if (!plan) {
    return (
      <Text color="gray.500" fontSize={{ base: "md", md: "sm" }}>
        {t("usersTable.noNextPlan")}
      </Text>
    );
  }

  const limit = !plan.data_limit
    ? t("unlimited")
    : formatBytes(plan.data_limit);

  return (
    <Stack spacing={1.5} minW={0}>
      <HStack spacing={2} flexWrap="wrap">
        <Badge
          colorScheme="teal"
          variant="subtle"
          textTransform="none"
          fontFamily="mono"
        >
          {limit}
        </Badge>
        <Text
          fontSize={{ base: "sm", md: "xs" }}
          color="gray.300"
          dir="ltr"
          sx={{ unicodeBidi: "isolate" }}
        >
          {formatTimestamp(plan.expire, i18n.language)}
        </Text>
      </HStack>
      <Text fontSize="xs" color="gray.400" lineHeight="1.6">
        {plan.add_remaining_traffic
          ? t("usersTable.keepRemainingTraffic")
          : t("usersTable.replaceRemainingTraffic")}
        {" · "}
        {plan.fire_on_either
          ? t("usersTable.activateOnEither")
          : t("usersTable.activateOnBoth")}
      </Text>
    </Stack>
  );
};

const ResetHistory: FC<{ user: User }> = ({ user }) => {
  const { t, i18n } = useTranslation();
  const history = [...(user.reset_history || [])].sort(
    (a, b) => new Date(b.reset_at).getTime() - new Date(a.reset_at).getTime()
  );

  if (history.length === 0) {
    return (
      <Text color="gray.500" fontSize="sm">
        {t("usersTable.noResetHistory")}
      </Text>
    );
  }

  return (
    <Popover isLazy placement="auto" strategy="fixed">
      <PopoverTrigger>
        <Button
          variant="link"
          colorScheme="teal"
          size="sm"
          minH="36px"
          fontSize="xs"
          onClick={(event) => event.stopPropagation()}
        >
          {t("usersTable.resetCount", { count: history.length })}
        </Button>
      </PopoverTrigger>
      <Portal>
        <PopoverContent
          dir={i18n.dir()}
          bg="#111d17"
          color="gray.100"
          borderColor="#475f50"
          maxW={{ base: "calc(100vw - 24px)", sm: "360px" }}
          onClick={(event) => event.stopPropagation()}
        >
          <PopoverArrow bg="#111d17" />
          <PopoverCloseButton />
          <PopoverHeader fontWeight="700" borderColor="#33483b" pe={10}>
            {t("usersTable.resetHistory")}
          </PopoverHeader>
          <PopoverBody maxH="280px" overflowY="auto" p={0}>
            {history.map((item, index) => (
              <Box key={`${item.reset_at}-${index}`} px={4} py={3}>
                <HStack justify="space-between" align="start" gap={4}>
                  <Text
                    fontSize={{ base: "md", md: "sm" }}
                    fontFamily="mono"
                    dir="ltr"
                    sx={{ unicodeBidi: "isolate" }}
                  >
                    {formatBytes(item.used_traffic)}
                  </Text>
                  <Text fontSize="xs" color="gray.400" textAlign="end">
                    {formatDateTime(item.reset_at, i18n.language)}
                  </Text>
                </HStack>
                {index < history.length - 1 && (
                  <Divider mt={3} borderColor="#33483b" />
                )}
              </Box>
            ))}
          </PopoverBody>
        </PopoverContent>
      </Portal>
    </Popover>
  );
};

type ActionButtonsProps = {
  user: User;
  onEdit: () => void;
};

const ActionButtons: FC<ActionButtonsProps> = ({ user, onEdit }) => {
  const { setQRCode, setSubLink } = useDashboard();
  const { t } = useTranslation();
  const proxyLinks = user.links.join("\r\n");
  const [copied, setCopied] = useState<[number, boolean]>([-1, false]);

  useEffect(() => {
    if (!copied[1]) return;
    const timer = window.setTimeout(() => setCopied([-1, false]), 1200);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const buttonStyle = {
    variant: "ghost",
    size: "sm",
    minW: "44px",
    h: "44px",
    color: "gray.300",
    borderRadius: "10px",
    bg: "transparent",
    borderWidth: "0",
    borderColor: "whiteAlpha.100",
    _hover: {
      bg: "rgba(45, 212, 191, .14)",
      color: "teal.200",
      borderColor: "rgba(45, 212, 191, .28)",
    },
    _focusVisible: { boxShadow: "0 0 0 2px var(--chakra-colors-teal-400)" },
    transition:
      "background-color 160ms ease, border-color 160ms ease, color 160ms ease",
  } as const;

  return (
    <HStack
      dir="ltr"
      justify="flex-start"
      spacing={1}
      flexWrap="wrap"
      onClick={(event) => event.stopPropagation()}
    >
      <CopyToClipboard
        text={
          user.subscription_url.startsWith("/")
            ? window.location.origin + user.subscription_url
            : user.subscription_url
        }
        onCopy={() => setCopied([0, true])}
      >
        <Box>
          <Tooltip
            label={
              copied[0] === 0 && copied[1]
                ? t("usersTable.copied")
                : t("usersTable.copyLink")
            }
            placement="top"
          >
            <IconButton
              {...buttonStyle}
              aria-label={t("usersTable.copyLink")}
              icon={
                copied[0] === 0 && copied[1] ? (
                  <CopiedIcon />
                ) : (
                  <SubscriptionLinkIcon />
                )
              }
            />
          </Tooltip>
        </Box>
      </CopyToClipboard>
      <CopyToClipboard text={proxyLinks} onCopy={() => setCopied([1, true])}>
        <Box>
          <Tooltip
            label={
              copied[0] === 1 && copied[1]
                ? t("usersTable.copied")
                : t("usersTable.copyConfigs")
            }
            placement="top"
          >
            <IconButton
              {...buttonStyle}
              aria-label={t("usersTable.copyConfigs")}
              icon={
                copied[0] === 1 && copied[1] ? <CopiedIcon /> : <CopyIcon />
              }
            />
          </Tooltip>
        </Box>
      </CopyToClipboard>
      <Tooltip label={t("usersTable.qrCode")} placement="top">
        <IconButton
          {...buttonStyle}
          aria-label={t("usersTable.qrCode")}
          icon={<QRIcon />}
          onClick={() => {
            setQRCode(user.links);
            setSubLink(user.subscription_url);
          }}
        />
      </Tooltip>
      <Tooltip label={t("userDialog.editUser")} placement="top">
        <IconButton
          {...buttonStyle}
          aria-label={t("userDialog.editUser")}
          icon={<EditIcon />}
          onClick={onEdit}
        />
      </Tooltip>
    </HStack>
  );
};

type UserCardProps = {
  user: User;
  selected: boolean;
  onSelectedChange: (selected: boolean) => void;
  expanded: boolean;
  onToggle: () => void;
  onOpen: () => void;
};

const UserCard: FC<UserCardProps> = ({
  user,
  selected,
  onSelectedChange,
  expanded,
  onToggle,
  onOpen,
}) => {
  const { t, i18n } = useTranslation();
  const reduceMotion = usePrefersReducedMotion();
  const owner = user.admin?.username || "—";
  const baseBorder = "rgba(100, 116, 139, .34)";

  return (
    <Card
      as="article"
      variant="outline"
      minW={0}
      maxW="full"
      overflow="hidden"
      position="relative"
      borderRadius="14px"
      borderColor={
        selected || expanded ? "rgba(45, 212, 191, .62)" : baseBorder
      }
      borderInlineStartWidth="1px"
      bg="rgba(8, 18, 28, .82)"
      backdropFilter="blur(18px)"
      boxShadow={
        expanded
          ? "0 14px 34px rgba(0, 0, 0, .34), 0 0 0 1px rgba(45, 212, 191, .1)"
          : "0 8px 22px rgba(0, 0, 0, .2)"
      }
      transition={
        reduceMotion ? "none" : "border-color 180ms ease, box-shadow 180ms ease"
      }
      _hover={{
        borderColor: "rgba(45, 212, 191, .5)",
        boxShadow: "0 12px 28px rgba(0, 0, 0, .3)",
      }}
    >
      <Box
        aria-hidden="true"
        position="absolute"
        top={0}
        insetInline={0}
        h="2px"
        bgGradient="linear(to-r, transparent, teal.400, cyan.300, transparent)"
        opacity={selected || expanded ? 1 : 0.58}
      />

      <Box
        w="full"
        minW={0}
        p={{ base: 3.5, md: 4 }}
        pt={{ base: 4, md: 4.5 }}
        textAlign="start"
      >
        <Stack spacing={3} minW={0}>
          <Box
            minW={0}
            p={3}
            borderRadius="12px"
            bg="rgba(15, 23, 42, .5)"
            backdropFilter="blur(12px)"
            borderWidth="1px"
            borderColor="rgba(148, 163, 184, .14)"
          >
            <UserIdentity
              user={user}
              owner={owner}
              selected={selected}
              onSelectedChange={onSelectedChange}
            />
          </Box>

          <UsagePanel
            used={user.used_traffic}
            total={user.data_limit}
            totalUsedTraffic={user.lifetime_used_traffic}
            dataLimitResetStrategy={user.data_limit_reset_strategy}
          />

          <ExpirationMeta user={user} />
        </Stack>
      </Box>

      <Flex
        dir="ltr"
        justify="space-between"
        align="center"
        gap={2}
        wrap="wrap"
        px={3}
        py={2}
        borderTopWidth="1px"
        borderColor="rgba(148, 163, 184, .14)"
        bg="rgba(2, 6, 23, .34)"
      >
        <ActionButtons user={user} onEdit={onOpen} />
        <Button
          dir={i18n.dir()}
          variant="outline"
          minH="44px"
          px={3}
          color="teal.100"
          bg="transparent"
          borderColor="rgba(45, 212, 191, .32)"
          fontSize="xs"
          aria-expanded={expanded}
          onClick={onToggle}
          _hover={{
            bg: "rgba(45, 212, 191, .1)",
            borderColor: "teal.300",
          }}
        >
          <HStack spacing={1.5}>
            <Text as="span">
              {expanded
                ? t("usersTable.hideDetails")
                : t("usersTable.showDetails")}
            </Text>
            <Box display="inline-flex" dir="ltr">
              <DetailsIcon
                aria-hidden="true"
                transform={expanded ? "rotate(180deg)" : undefined}
                transition={reduceMotion ? "none" : "transform 180ms ease"}
              />
            </Box>
          </HStack>
        </Button>
      </Flex>

      <Collapse in={expanded} animateOpacity={!reduceMotion}>
        <Box
          px={4}
          py={4}
          borderTopWidth="1px"
          borderColor="rgba(45, 212, 191, .24)"
          bg="rgba(2, 6, 23, .46)"
        >
          <SimpleGrid columns={1} gap={3} minW={0}>
            <DetailSection
              title={t("usersTable.accountActivity")}
              icon={<AccountIcon />}
            >
              <SimpleGrid columns={{ base: 1, sm: 2 }} gap={3.5} minW={0}>
                <DetailItem label={t("usersTable.admin")}>
                  <Text
                    fontSize="sm"
                    fontWeight="700"
                    dir="ltr"
                    textAlign="start"
                    overflowWrap="anywhere"
                    sx={{ unicodeBidi: "isolate" }}
                  >
                    {owner}
                  </Text>
                </DetailItem>
                <DetailItem
                  label={t("usersTable.createdAt")}
                  icon={<ExpirationIcon />}
                >
                  <Text fontSize={{ base: "md", md: "sm" }} lineHeight="1.7">
                    {formatDateTime(user.created_at, i18n.language)}
                  </Text>
                </DetailItem>
              </SimpleGrid>
            </DetailSection>

            <DetailSection
              title={t("usersTable.subscriptionDetails")}
              icon={<SubscriptionIcon />}
            >
              <Stack
                spacing={3.5}
                divider={<Divider borderColor="whiteAlpha.100" />}
              >
                <DetailItem label={t("usersTable.subscriptionUpdatedAt")}>
                  <Text fontSize={{ base: "md", md: "sm" }} lineHeight="1.7">
                    {formatDateTime(user.sub_updated_at, i18n.language)}
                  </Text>
                </DetailItem>
                <DetailItem
                  label={t("usersTable.lastUserAgent")}
                  icon={<DeviceIcon />}
                >
                  <Text
                    fontSize={{ base: "md", md: "sm" }}
                    dir="ltr"
                    textAlign="start"
                    lineHeight="1.7"
                    overflowWrap="anywhere"
                    sx={{ unicodeBidi: "isolate" }}
                  >
                    {user.sub_last_user_agent || "—"}
                  </Text>
                </DetailItem>
              </Stack>
            </DetailSection>

            <DetailSection
              title={t("usersTable.planAndResets")}
              icon={<PlanIcon />}
            >
              <Stack
                spacing={3.5}
                divider={<Divider borderColor="whiteAlpha.100" />}
              >
                <DetailItem label={t("usersTable.nextPlan")}>
                  <NextPlanSummary user={user} />
                </DetailItem>
                <DetailItem label={t("usersTable.resetHistory")}>
                  <ResetHistory user={user} />
                </DetailItem>
              </Stack>
            </DetailSection>
          </SimpleGrid>
        </Box>
      </Collapse>
    </Card>
  );
};

const EmptySection: FC<{ isFiltered: boolean }> = ({ isFiltered }) => {
  const { onCreateUser } = useDashboard();
  const { t } = useTranslation();
  return (
    <VStack px={5} py={12} spacing={4} textAlign="center">
      <EmptySectionIcon
        maxH="150px"
        maxW="150px"
        aria-hidden="true"
        _dark={{
          'path[fill="#fff"]': { fill: "gray.800" },
          'path[fill="#f2f2f2"], path[fill="#e6e6e6"], path[fill="#ccc"]': {
            fill: "gray.700",
          },
          'circle[fill="#3182CE"]': { fill: "primary.300" },
        }}
        _light={{
          'path[fill="#f2f2f2"], path[fill="#e6e6e6"], path[fill="#ccc"]': {
            fill: "gray.300",
          },
          'circle[fill="#3182CE"]': { fill: "primary.500" },
        }}
      />
      <Text color="gray.600" _dark={{ color: "gray.300" }} maxW="52ch">
        {isFiltered ? t("usersTable.noUserMatched") : t("usersTable.noUser")}
      </Text>
      {!isFiltered && (
        <Button
          size="sm"
          colorScheme="primary"
          onClick={() => onCreateUser(true)}
        >
          {t("createUser")}
        </Button>
      )}
    </VStack>
  );
};

type UsersTableProps = BoxProps;

export const UsersTable: FC<UsersTableProps> = (props) => {
  const {
    filters,
    users: { users },
    onEditingUser,
  } = useDashboard();
  const { i18n } = useTranslation();
  const direction = i18n.dir();
  const isFiltered = Boolean(
    filters.search ||
      filters.status ||
      filters.admin ||
      filters.sort !== "-created_at"
  );
  const [expandedUser, setExpandedUser] = useState<string | null>(null);
  const [selectedUsernames, setSelectedUsernames] = useState<Set<string>>(
    () => new Set()
  );
  const selectedUsers = users.filter((user) =>
    selectedUsernames.has(user.username)
  );
  const allVisibleSelected =
    users.length > 0 &&
    users.every((user) => selectedUsernames.has(user.username));

  useEffect(() => {
    const visible = new Set(users.map((user) => user.username));
    setSelectedUsernames(
      (current) =>
        new Set([...current].filter((username) => visible.has(username)))
    );
  }, [users]);

  const setUserSelected = (username: string, selected: boolean) => {
    setSelectedUsernames((current) => {
      const next = new Set(current);
      if (selected) next.add(username);
      else next.delete(username);
      return next;
    });
  };

  const toggleAllVisible = (selected: boolean) => {
    setSelectedUsernames(
      selected ? new Set(users.map((user) => user.username)) : new Set()
    );
  };

  return (
    <Box
      {...props}
      id="users-table"
      dir={direction}
      w="full"
      maxW="full"
      minW={0}
      overflowX="hidden"
      borderTopWidth="1px"
      borderColor="gray.200"
      _dark={{ borderColor: "#33483b" }}
    >
      {users.length === 0 ? (
        <EmptySection isFiltered={isFiltered} />
      ) : (
        <>
          <BulkUserActions
            users={selectedUsers}
            allVisibleSelected={allVisibleSelected}
            visibleCount={users.length}
            onToggleAll={toggleAllVisible}
            onClear={() => setSelectedUsernames(new Set())}
          />
          <SimpleGrid
            columns={{ base: 1, lg: 2, "2xl": 3 }}
            gap={{ base: 3, md: 4 }}
            w="full"
            maxW="full"
            minW={0}
            py={4}
            alignItems="start"
          >
            {users.map((user) => (
              <UserCard
                key={user.username}
                user={user}
                selected={selectedUsernames.has(user.username)}
                onSelectedChange={(selected) =>
                  setUserSelected(user.username, selected)
                }
                expanded={expandedUser === user.username}
                onToggle={() =>
                  setExpandedUser((current) =>
                    current === user.username ? null : user.username
                  )
                }
                onOpen={() => onEditingUser(user)}
              />
            ))}
          </SimpleGrid>
        </>
      )}
      <Pagination />
    </Box>
  );
};
