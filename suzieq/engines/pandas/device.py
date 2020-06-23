import pandas as pd
import numpy as np
from suzieq.engines.pandas.engineobj import SqEngineObject


class DeviceObj(SqEngineObject):

    def summarize(self, **kwargs):
        """Summarize device information across namespace"""

        self._init_summarize(self.iobj._table, **kwargs)
        if self.summary_df.empty:
            return self.summary_df

        self._summarize_on_add_field = [
            ('deviceCnt', 'hostname', 'nunique'),
        ]

        self._summarize_on_add_list_or_count = [
            ('vendorCnt', 'vendor'),
            ('modelCnt', 'model'),
            ('archCnt', 'architecture'),
            ('versionCnt', 'version'),
        ]

        uptime_cols = (self.summary_df['timestamp'] -
                       pd.to_datetime(self.summary_df['bootupTimestamp']*1000,
                                      unit='ms'))
        uptime_cols = pd.to_timedelta(uptime_cols, unit='ms')
        self.summary_df.insert(len(self.summary_df.columns)-1,
                               'uptime', uptime_cols)

        self._summarize_on_add_stat = [
            ('upTimeStat', '', 'uptime')
        ]

        self._gen_summarize_data()
        self._post_summarize(check_empty_col='deviceCnt')
        return self.ns_df.convert_dtypes()
