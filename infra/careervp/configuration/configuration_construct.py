from pathlib import Path

from aws_cdk import Duration, RemovalPolicy, Tags
from aws_cdk import aws_appconfig as appconfig
from constructs import Construct

from .schema import FeatureFlagsConfiguration
from .. import constants
from ..scratch_deployment import ScratchDeploymentSettings, validate_scratch_boundary

# AWS::AppConfig::Deployment treats Tags as an immutable (replacement-
# triggering) property, same as the CE anomaly resources (see monitoring.py
# _P32_ANOMALY_OWNER_TAG). Pin its owner tag to the deploy identity CI
# actually uses so a human running cdk diff/deploy locally doesn't propose
# replacing a live config rollout just from a tag-identity mismatch
# (see P-23 ledger step 1.0, 2026-07-18).
_APPCONFIG_DEPLOYMENT_OWNER_TAG = "runner"


class ConfigurationStore(Construct):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        environment: str,
        service_name: str,
        configuration_name: str,
        configuration_source: str | None = None,
        scratch_settings: ScratchDeploymentSettings | None = None,
    ) -> None:
        """
        This construct should be deployed in a different repo and have its own pipeline so updates can be decoupled from
        running the service pipeline and without redeploying the service lambdas.

        Args:
            scope (Construct): The scope in which to define this construct.
            id_ (str): The scoped construct ID. Must be unique amongst siblings. If the ID includes a path separator (``/``), then it will be
                        replaced by double dash ``--``.
            environment (str): environment name. Used for loading the corresponding JSON file to upload under
                               'configuration/json/{environment}_configuration.json'
            service_name (str): application name.
            configuration_name (str): configuration name
        """
        super().__init__(scope, id_)

        if scratch_settings is not None:
            validate_scratch_boundary(scratch_settings, environment=environment)
        elif configuration_source is not None and configuration_source != environment:
            raise ValueError(
                "a configuration source override requires validated scratch settings"
            )

        configuration_str = self._get_and_validate_configuration(
            configuration_source or environment
        )
        self.app_name = f"{id_}{service_name}"
        self.config_app = appconfig.Application(
            self,
            id=self.app_name,
            application_name=self.app_name[:64],
        )

        self.config_env = appconfig.Environment(
            self,
            id=f"{id_}env",
            application=self.config_app,
            environment_name=environment,
            deletion_protection_check=appconfig.DeletionProtectionCheck.BYPASS,
        )

        # zero minutes, zero bake, 100 growth all at once
        self.config_dep_strategy = appconfig.DeploymentStrategy(
            self,
            f"{id_}zero",
            rollout_strategy=appconfig.RolloutStrategy.linear(
                growth_factor=100,
                deployment_duration=Duration.minutes(0),
                final_bake_time=Duration.minutes(0),
            ),
        )

        self.config = appconfig.HostedConfiguration(
            self,
            f"{id_}version",
            application=self.config_app,
            name=configuration_name,
            content=appconfig.ConfigurationContent.from_inline(configuration_str),
            type=appconfig.ConfigurationType.FREEFORM,
            deployment_strategy=self.config_dep_strategy,
            deploy_to=[self.config_env],
        )
        deployments = [
            node
            for node in self.config.node.find_all()
            if isinstance(node, appconfig.CfnDeployment)
        ]
        for deployment in deployments:
            Tags.of(deployment).add(
                constants.OWNER_TAG, _APPCONFIG_DEPLOYMENT_OWNER_TAG
            )
        if scratch_settings is not None:
            hosted_versions = [
                node
                for node in self.config.node.find_all()
                if isinstance(node, appconfig.CfnHostedConfigurationVersion)
            ]
            if len(hosted_versions) != 1:
                raise ValueError(
                    "scratch teardown expected one AppConfig hosted version; "
                    f"found {len(hosted_versions)}"
                )
            hosted_versions[0].apply_removal_policy(RemovalPolicy.DESTROY)

    def _get_and_validate_configuration(self, environment: str) -> str:
        current = Path(__file__).parent
        conf_filepath = current / (f"json/{environment}_configuration.json")
        configuration_str = conf_filepath.read_text()
        # validate configuration (check feature flags schema structure if exists)
        FeatureFlagsConfiguration.model_validate_json(configuration_str)
        return configuration_str
