# it's not clear wether these tags need to live in the SDK since they are a property of the model
# meanwhile they are hardcoded in simwork and it makes sense to have them here
# they also seem to be assumed in the logic of generating a vpopdesign from a CM
import enum

class ModelInputTag(enum.Enum):
    ModelIntrinsic = "eff3df9d-146a-4b80-bf90-a72702c572a3"
    PatientDescriptorKnown = "a8124dc4-4cbe-4928-a449-2740ee52460b"
    PatientDescriptorPartiallyKnown = "c5599725-db82-4152-b93e-1b3acdb8d548"
    PatientDescriptorUnknown = "cbf09d2a-a54a-4838-9c43-cfc87dbe2c53"
    Formulaic = "ff4e9040-4d92-42fc-8131-20af3cf0643d"
    ProtocolSpecific = "13e427c2-7860-4cf5-a3e2-e38fcfca3dd6"
    Technical = "ed82d7ad-8263-49bf-b8d6-c3c3d8e3ddb1"

class ModelStatusTag(enum.Enum):
    Draft = "7789cdb4-e9c5-4226-b3f0-cd4b786445b4"
    NeedReview = "b4f169e6-4769-4a4a-8a3c-5ebea6b848bd"
    Reviewed = "3c7df28a-62bb-4a5d-b3ff-dc89a5d39a09"
    Obsolete = "c45fda31-da54-4447-9974-ec38e96c9535"

